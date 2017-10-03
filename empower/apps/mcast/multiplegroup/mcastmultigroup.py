#!/usr/bin/env python3
#
# Copyright (c) 2016, Estefanía Coronado
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the CREATE-NET nor the
#      names of its contributors may be used to endorse or promote products
#      derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY CREATE-NET ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL CREATE-NET BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Multicast management app with handover support."""

import tornado.web
import tornado.httpserver
import time
import datetime
import sys
import statistics
import math

from empower.core.app import EmpowerApp
from empower.core.resourcepool import TX_MCAST
from empower.core.resourcepool import TX_MCAST_DMS
from empower.core.resourcepool import TX_MCAST_LEGACY
from empower.core.resourcepool import TX_MCAST_DMS_H
from empower.core.resourcepool import TX_MCAST_LEGACY_H
from empower.core.tenant import T_TYPE_SHARED
from empower.datatypes.etheraddress import EtherAddress
from empower.main import RUNTIME
from empower.apps.mcast.mcastwtp import MCastWTPInfo
from empower.apps.mcast.mcastclient import MCastClientInfo
from empower.main import RUNTIME

from empower.igmp_report.igmp_report import V3_MODE_IS_INCLUDE
from empower.igmp_report.igmp_report import V3_MODE_IS_EXCLUDE
from empower.igmp_report.igmp_report import V3_CHANGE_TO_INCLUDE_MODE
from empower.igmp_report.igmp_report import V3_CHANGE_TO_EXCLUDE_MODE
from empower.igmp_report.igmp_report import V3_ALLOW_NEW_SOURCES
from empower.igmp_report.igmp_report import V3_BLOCK_OLD_SOURCES
from empower.igmp_report.igmp_report import V2_JOIN_GROUP
from empower.igmp_report.igmp_report import V2_LEAVE_GROUP
from empower.igmp_report.igmp_report import V1_MEMBERSHIP_REPORT
from empower.igmp_report.igmp_report import V1_V2_MEMBERSHIP_QUERY

import empower.logger
LOG = empower.logger.get_logger()

MCAST_EWMA_PROB = "ewma"
MCAST_CUR_PROB = "cur_prob"


class MCastMultigroup(EmpowerApp):


    """Multicast app with rate adaptation support.

    Command Line Parameters:

        period: loop period in ms (optional, default 5000ms)

    Example:

        (old) ./empower-runtime.py apps.mcast.mcast:52313ecb-9d00-4b7d-b873-b55d3d9ada26
        (new) ./empower-runtime.py apps.mcast.mcastsimplemultgroup --tenant_id=52313ecb-9d00-4b7d-b873-b55d3d9ada00

    """

    def __init__(self, **kwargs):

        EmpowerApp.__init__(self, **kwargs)
        self.__mcast_clients = list()
        self.__mcast_wtps = list()
        self.__prob_thershold = 95
        self.__every = 50
        self.__period_length = 3000
        self.__dms_min_length = 200
        self.__dms_max_length = 500

        # Register an lvap join event
        self.lvapjoin(every=500, callback=self.lvap_join_callback)
        self.lvapleave(every=500,callback=self.lvap_leave_callback)
        # Register an wtp up event
        self.wtpup(every=500, callback=self.wtp_up_callback)
        self.wtpdown(every=500,callback=self.wtp_down_callback)

        self.incom_mcast_addr(every=500, callback=self.incom_mcast_addr_callback)

        self.empower_igmp_record_type = { V3_MODE_IS_INCLUDE : self.mcast_addr_unregister,
            V3_MODE_IS_EXCLUDE : self.mcast_addr_register,
            V3_CHANGE_TO_INCLUDE_MODE : self.mcast_addr_unregister,
            V3_CHANGE_TO_EXCLUDE_MODE : self.mcast_addr_register,
            V3_ALLOW_NEW_SOURCES : self.mcast_addr_query,
            V3_BLOCK_OLD_SOURCES : self.mcast_addr_query,
            V2_JOIN_GROUP : self.mcast_addr_register,
            V2_LEAVE_GROUP : self.mcast_addr_unregister,
            V1_MEMBERSHIP_REPORT : self.mcast_addr_register,
            V1_V2_MEMBERSHIP_QUERY : self.mcast_addr_query
        }

    @property
    def mcast_clients(self):
        """Return current multicast clients."""
        return self.__mcast_clients

    @mcast_clients.setter
    def mcast_clients(self, mcast_clients_info):
        self.__mcast_clients = mcast_clients_info

    @property
    def mcast_wtps(self):
        """Return current multicast wtps."""
        return self.__mcast_wtps

    @mcast_wtps.setter
    def mcast_wtps(self, mcast_wtps_info):
        self.__mcast_wtps = mcast_wtps_info

    @property
    def prob_thershold(self):
        """Return current probability thershold."""
        return self.__prob_thershold

    @prob_thershold.setter
    def prob_thershold(self, prob_thershold):
        self.__prob_thershold = prob_thershold

    @property
    def every(self):
        """Return every period: the loop method is called every "every" ms."""
        return self.__every

    @every.setter
    def every(self, every):
        self.__every = every

    @property
    def period_length(self):
        """Return the total amount of time considering both dms and legacy policies."""
        return self.__period_length

    @period_length.setter
    def period_length(self, period_length):
        self.__period_length = period_length

    @property
    def dms_min_length(self):
        """Return the minimum duration for the DMS period."""
        return self.__dms_min_length

    @dms_min_length.setter
    def dms_min_length(self, dms_min_length):
        self.__dms_min_length = dms_min_length

    @property
    def dms_max_length(self):
        """Return the maximum duration for the DMS period according to the period length."""
        return self.__dms_max_length

    @dms_max_length.setter
    def dms_max_length(self, dms_max_length):
        self.__dms_max_length = dms_max_length

    def incom_mcast_addr_callback(self, request):
        #self.log.info("New multicast address %s from WTP %s", request.mcast_addr, request.wtp)

        if request.wtp not in RUNTIME.tenants[self.tenant.tenant_id].wtps:
            return
        wtp = RUNTIME.tenants[self.tenant.tenant_id].wtps[request.wtp]

        for block in wtp.supports:
            if any(entry.block.hwaddr == block.hwaddr for entry in self.mcast_wtps):
                continue
            self.wtp_register(block)

        self.mcast_addr_register(None, request.mcast_addr, wtp)

    def igmp_report_callback(self, request):
        # self.log.info("IGMP report type %d for multicast address %s from %s in WTP %s", 
        #     request.igmp_type, request.mcast_addr, request.sta, request.wtp)

        if request.wtp not in RUNTIME.tenants[self.tenant.tenant_id].wtps:
            return
        if request.sta not in RUNTIME.lvaps:
            return

        wtp = RUNTIME.tenants[self.tenant.tenant_id].wtps[request.wtp]
        lvap = RUNTIME.lvaps[request.sta]

        if request.igmp_type not in self.empower_igmp_record_type:
            return
        self.empower_igmp_record_type[request.igmp_type](lvap.addr, request.mcast_addr, wtp)

    def txp_bin_counter_callback(self, counter):
        """Counters callback."""

        # self.log.info("Mcast address %s packets %u bytes %u", counter.mcast,
        #               counter.tx_packets[0], counter.tx_bytes[0])

        for index, entry in enumerate(self.mcast_wtps):
            if entry.block.hwaddr == counter.block.hwaddr:
                if counter.mcast in entry.last_txp_bin_tx_pkts_counter:
                    entry.last_tx_pkts[counter.mcast] = counter.tx_packets[0] - entry.last_txp_bin_tx_pkts_counter[counter.mcast]
                else:
                    entry.last_tx_pkts[counter.mcast] = counter.tx_packets[0]
                entry.last_txp_bin_tx_pkts_counter[counter.mcast] = counter.tx_packets[0]
                if counter.mcast in entry.last_txp_bin_tx_bytes_counter:
                    entry.last_tx_bytes[counter.mcast] = counter.tx_bytes[0] - entry.last_txp_bin_tx_bytes_counter[counter.mcast]
                else:
                    entry.last_tx_bytes[counter.mcast] = counter.tx_bytes[0]
                entry.last_txp_bin_tx_bytes_counter[counter.mcast] = counter.tx_bytes[0]
                break

    def wtp_up_callback(self, wtp):
        """Called when a new WTP connects to the controller."""
        for block in wtp.supports:
            if any(entry.block.hwaddr == block.hwaddr for entry in self.mcast_wtps):
                continue

            self.wtp_register(block)         

    def wtp_down_callback(self, wtp):
        """Called when a wtp connectdiss from the controller."""

        for index, entry in enumerate(self.mcast_wtps):
            for block in wtp.supports:
                if block.hwaddr == entry.block.hwaddr:
                    del self.mcast_wtps[index]
                    break

    def lvap_join_callback(self, lvap):
        """ New LVAP. """

        if any(lvap.addr == entry.addr for entry in self.mcast_clients):
            return

        lvap.lvap_stats(every=50, callback=self.lvap_stats_callback)
        self.igmp_report(every=500, callback=self.igmp_report_callback)

        default_block = next(iter(lvap.downlink))
        lvap_info = MCastClientInfo()

        lvap_info.addr = lvap.addr
        lvap_info.attached_hwaddr = default_block.hwaddr
        self.mcast_clients.append(lvap_info)

        for index, entry in enumerate(self.mcast_wtps):
            if entry.block.hwaddr == default_block.hwaddr:
                entry.attached_clients = entry.attached_clients + 1
                break

    def lvap_leave_callback(self, lvap):
        """Called when an LVAP disassociates from a tennant."""

        default_block = next(iter(lvap.downlink))
        mcast_addresses_in_use = list()
        current_wtp = None

        for index, entry in enumerate(self.mcast_clients):
            if entry.addr == lvap.addr:
                del self.mcast_clients[index]
                mcast_addresses_in_use = entry.multicast_services
                break

        for wtp in RUNTIME.tenants[self.tenant_id].wtps.values():
            for block in wtp.supports:
                if default_block.hwaddr == block.hwaddr:
                    current_wtp = wtp
                    break

        for index, entry in enumerate(self.mcast_wtps):
            if entry.block.hwaddr == default_block.hwaddr:
                entry.block.radio.connection.send_del_mcast_receiver(lvap.addr, current_wtp, default_block.hwaddr, default_block.channel, default_block.band)
                entry.attached_clients = entry.attached_clients - 1
                if entry.attached_clients == 0:
                    return
                # In case that this was not the only client attached to this WTP, the rate must be recomputed. 
                if not mcast_addresses_in_use:
                    return
                for i, addr in enumerate(mcast_addresses_in_use):
                    tx_policy = entry.block.tx_policies[addr]
                    ewma_rate, cur_prob_rate = self.calculate_wtp_rate(entry, addr)
                    tx_policy.mcast = TX_MCAST_LEGACY
                    if entry.prob_measurement[addr] == MCAST_EWMA_PROB:
                        tx_policy.mcs = [int(ewma_rate)]
                    elif entry.prob_measurement[addr] == MCAST_CUR_PROB:
                        tx_policy.mcs = [int(cur_prob_rate)]
                    entry.rate[addr] = ewma_rate
                    entry.cur_prob_rate[addr] = cur_prob_rate
                    entry.mode[addr] = TX_MCAST_LEGACY_H
                    break
                break

    def lvap_stats_callback(self, counter):
        """ New stats available. """

        rates = (counter.to_dict())["rates"]
        if not rates or counter.lvap not in RUNTIME.lvaps:
            return

        highest_prob = 0
        highest_rate = 0
        highest_cur_prob = 0
        sec_highest_rate = 0
        higher_thershold_ewma_rates = []
        higher_thershold_ewma_prob = []
        higher_thershold_cur_prob_rates = []
        higher_thershold_cur_prob = []
        lowest_rate = min(int(float(key)) for key in rates.keys())
        available_rates = sorted(rates.keys())
        second_highest_prob = 0
        second_highest_rate = 0

        # Looks for the rate that has the highest ewma prob. for the station.
        # If two rates have the same probability, the highest one is selected. 
        # Stores in a list the rates whose ewma prob. is higher than a certain thershold.
        for key, entry in rates.items():  #key is the rate
            if (rates[key]["prob"] > highest_prob) or \
            (rates[key]["prob"] == highest_prob and int(float(key)) > highest_rate):
                second_highest_rate = highest_rate
                second_highest_prob = highest_prob
                highest_rate = int(float(key))
                highest_prob = rates[key]["prob"]
            if (int(float(rates[key]["prob"]))) >= self.prob_thershold:
                higher_thershold_ewma_rates.append(int(float(key)))
                higher_thershold_ewma_prob.append(rates[key]["prob"])

        # Looks for the rate that has the highest cur prob and is lower than the one selected
        # for the ewma prob for the station.
        # Stores in a list the rates whose cur prob. is higher than thershold%.
        for key, entry in rates.items():
            if rates[key]["cur_prob"] > highest_cur_prob or \
            (rates[key]["cur_prob"] == highest_cur_prob and int(float(key)) > sec_highest_rate):
                sec_highest_rate = int(float(key))
                highest_cur_prob = rates[key]["cur_prob"] 
            if (int(float(rates[key]["cur_prob"]))) >= self.prob_thershold:
                higher_thershold_cur_prob_rates.append(int(float(key)))
                higher_thershold_cur_prob.append(rates[key]["cur_prob"])  

        if (highest_prob < self.prob_thershold) and (rates[str(float(highest_rate))]["cur_prob"] < self.prob_thershold) and (highest_rate > 12):
            rate_index = [i for i,x in enumerate(available_rates) if x == str(float(highest_rate))][-1]
            highest_rate = int(float(available_rates[(rate_index - 1)]))

        if highest_rate == 9:
            highest_rate = 12

        # if (highest_prob < self.prob_thereshold):
        #     highest_rate = second_highest_rate
        #     highest_prob = second_highest_prob

        if highest_cur_prob == 0 and highest_prob == 0:
            highest_rate = lowest_rate
            sec_highest_rate = lowest_rate
        elif highest_cur_prob == 0 and highest_prob != 0:
            sec_highest_rate = highest_rate

        # The information of the client is updated with the new statistics
        lvap = RUNTIME.lvaps[counter.lvap]
        for index, entry in enumerate(self.mcast_clients):
            if entry.addr == counter.lvap:
                entry.highest_rate = int(highest_rate)
                entry.rates = rates
                entry.highest_cur_prob_rate = int(sec_highest_rate)
                entry.higher_thershold_ewma_rates = higher_thershold_ewma_rates
                entry.higher_thershold_cur_prob_rates = higher_thershold_cur_prob_rates
                break

    def mcast_addr_register(self, sta, mcast_addr, wtp):
        for block in wtp.supports:
            for index, entry in enumerate(self.mcast_wtps):
                if entry.block.hwaddr == block.hwaddr:
                    if mcast_addr not in entry.managed_mcast_addresses:
                        tx_policy = entry.block.tx_policies[mcast_addr]
                        tx_policy.mcast = TX_MCAST_LEGACY
                        tx_policy.mcs = [min(list(block.supports))]
                        entry.prob_measurement[mcast_addr] = MCAST_EWMA_PROB
                        entry.mode[mcast_addr] = TX_MCAST_LEGACY_H
                        entry.rate[mcast_addr] = min(entry.block.supports)
                        entry.cur_prob_rate[mcast_addr] = min(entry.block.supports)
                        entry.managed_mcast_addresses.append(mcast_addr)
                        self.txp_bin_counter(block=entry.block,
                            mcast=mcast_addr,
                            callback=self.txp_bin_counter_callback,
                            every=500)
                        period = self.lookup_mcast_period(entry)
                        if period != None:
                            entry.dms_starting_period[mcast_addr] = period
                        else:
                            self.multicast_periods_management(entry)
                        break

        for index, entry in enumerate(self.mcast_clients):
            if sta is not None and entry.addr == sta and mcast_addr not in entry.multicast_services:
                entry.multicast_services.append(mcast_addr)
                break

    def lookup_mcast_period(self, mcast_wtp):
        periods = [i for i in range(0, (mcast_wtp.dms_max_period + mcast_wtp.legacy_max_period), mcast_wtp.dms_max_period)]
        periods_busyness = [{period: False} for period in periods]

        for index, entry in enumerate(periods_busyness):
            period = next(iter(entry))
            if period in list(mcast_wtp.dms_starting_period.values()):
                entry[period] = True

        for index, entry in enumerate(periods_busyness):
            period = next(iter(entry))
            if entry[period] is False:
                return period
        return None

    def mcast_addr_unregister(self, sta, mcast_addr, wtp):
        addr_in_use = False

        for index, entry in enumerate(self.mcast_clients):
            if entry.addr == sta and mcast_addr in entry.multicast_services:
                entry.multicast_services.remove(mcast_addr)
            elif entry.addr != sta and mcast_addr in entry.multicast_services:
                addr_in_use = True

        # for block in wtp.supports:
        #     for index, entry in enumerate(self.mcast_wtps):
        #         # If there are not clients requesting the service and there is not any ongoing transmission using that address
        #         # The address can be removed. The signal must be sent to the corresponding AP
        #         if entry.block.hwaddr == block.hwaddr and  mcast_addr in entry.managed_mcast_addresses and addr_in_use is False and \
        #         entry.last_tx_bytes[mcast_addr] == 0 and entry.last_tx_pkts[mcast_addr] == 0:
        #             entry.managed_mcast_addresses.remove(mcast_addr)
        #             del entry.mode[mcast_addr]
        #             del entry.rate[mcast_addr]
        #             del entry.cur_prob_rate[mcast_addr]
        #             del entry.prob_measurement[mcast_addr]
        #             del entry.last_tx_bytes[mcast_addr]
        #             del entry.last_txp_bin_tx_bytes_counter[mcast_addr]
        #             del entry.last_tx_pkts[mcast_addr]
        #             del entry.last_txp_bin_tx_pkts_counter[mcast_addr]
        #             self.multicast_periods_management(entry)
        #             entry.block.radio.connection.send_del_mcast_addr(mcast_addr, wtp, block.hwaddr, block.channel, block.band)
        #             break

    def mcast_addr_query(self, sta, mcast_addr, wtp):
        pass

    def wtp_register(self, block):
        wtp_info = MCastWTPInfo()
        wtp_info.block = block
        wtp_info.dms_max_period = max(int(math.ceil(self.dms_min_length / self.every)), int(self.dms_max_length / self.every))
        wtp_info.legacy_max_period = max(int(self.period_length / self.every) - wtp_info.dms_max_period, 1)
        self.mcast_wtps.append(wtp_info)

    def loop(self):
        """ Periodic job. """
        for index, entry in enumerate(self.mcast_wtps):
            if not entry.managed_mcast_addresses:
                continue

            entry.current_period = entry.next_period
            for i, addr in enumerate(entry.managed_mcast_addresses):
                tx_policy = entry.block.tx_policies[addr]

                # if addr in entry.last_tx_bytes and addr in entry.last_tx_pkts and \
                # entry.last_tx_bytes[addr] == 0 and entry.last_tx_pkts[addr] == 0:
                #     tx_policy.mcast = TX_MCAST_LEGACY
                #     tx_policy.mcs = [min(entry.block.supports)]
                    # if addr not in entry.unused_addresses.items():
                    #     entry.unused_addresses[addr] = 1
                    # else:
                    #     if entry.unused_addresses[addr] >= 10:
                    #         self.mcast_addr_unregister()
                    #     else:
                    #         entry.unused_addresses[addr] += 1
                if (entry.current_period >= entry.dms_starting_period[addr]) and \
                (entry.current_period < (entry.dms_starting_period[addr] + entry.dms_max_period)):
                    tx_policy.mcast = TX_MCAST_DMS
                    entry.mode[addr] = TX_MCAST_DMS_H
                elif (entry.current_period < entry.dms_starting_period[addr]) or \
                    (entry.current_period >= (entry.dms_starting_period[addr] + entry.dms_max_period)):
                    if tx_policy.mcast == TX_MCAST_DMS:
                        ewma_rate, cur_prob_rate = self.calculate_wtp_rate(entry, addr)
                        if entry.prob_measurement[addr] == MCAST_EWMA_PROB:
                            tx_policy.mcs = [int(ewma_rate)]
                        elif entry.prob_measurement[addr] == MCAST_CUR_PROB:
                            tx_policy.mcs = [int(cur_prob_rate)]
                        entry.rate[addr] = ewma_rate
                        entry.cur_prob_rate[addr] = cur_prob_rate
                    tx_policy.mcast = TX_MCAST_LEGACY
                    entry.mode[addr] = TX_MCAST_LEGACY_H

            entry.next_period = (entry.next_period + 1) % (entry.dms_max_period + entry.legacy_max_period)

    def multicast_periods_management(self, mcast_wtp):
        overlap = False # True when there are more multicast addresses than the maximum number of periods (dms + legacy periods)
        block = 0   # Beginning of the DMS period for each address in this AP

        if len(mcast_wtp.managed_mcast_addresses) > 0:
            dms_period = max(int(math.ceil(self.dms_min_length / self.every)), min(int(self.dms_max_length / self.every), int((self.period_length / len(mcast_wtp.managed_mcast_addresses)) / self.every)))
        else:
            dms_period = max(int(math.ceil(self.dms_min_length / self.every)), int(self.dms_max_length / self.every))
        legacy_period = max(int(self.period_length / self.every) - dms_period, 1)

        # Period overlap detection
        total_length = self.every * (dms_period + legacy_period)
        if self.every * dms_period * len(mcast_wtp.managed_mcast_addresses) > total_length:
            overlap = True

        #if not duplicates and not overlap:
        if not overlap and mcast_wtp.dms_max_period == dms_period and mcast_wtp.legacy_max_period == legacy_period:
            return

        # If there are duplicate periods but there is no overlap, periods must be only rescheduled
        mcast_wtp.dms_max_period = dms_period
        mcast_wtp.legacy_max_period = legacy_period

        if len(mcast_wtp.managed_mcast_addresses) == 0:
            return

        for index, entry in enumerate(mcast_wtp.managed_mcast_addresses):
            mcast_wtp.dms_starting_period[entry] = (block * mcast_wtp.dms_max_period)
            if block < (((mcast_wtp.legacy_max_period + mcast_wtp.dms_max_period) // mcast_wtp.dms_max_period) - 1):
                block = block + 1
            else:
                block = 0

    def calculate_wtp_rate(self, mcast_wtp, addr):
        min_rate = best_rate = min_highest_cur_prob_rate = best_highest_cur_prob_rate = sys.maxsize
        thershold_intersection_list = []
        thershold_highest_cur_prob_rate_intersection_list = []
        highest_thershold_valid = True
        second_thershold_valid = True

        for index, entry in enumerate(self.mcast_clients):
            if entry.attached_hwaddr == mcast_wtp.block.hwaddr and addr in entry.multicast_services:
                # It looks for the lowest rate among all the receptors just in case in there is no valid intersection
                # for the best rates of the clients (for both the ewma and cur probabilities). 
                if entry.highest_rate < min_rate and entry.highest_rate != 0:
                    min_rate = entry.highest_rate
                if entry.highest_cur_prob_rate < min_highest_cur_prob_rate and entry.highest_cur_prob_rate != 0:
                    min_highest_cur_prob_rate = entry.highest_cur_prob_rate

                # It checks if there is a possible intersection among the clients rates for the emwa prob.
                if highest_thershold_valid is True:
                    # If a given client does not have any rate higher than the required prob (e.g. thershold% for emwa)
                    # it is assumed that there is no possible intersection
                    if not entry.higher_thershold_ewma_rates:
                        highest_thershold_valid = False
                    elif not thershold_intersection_list:
                        thershold_intersection_list = entry.higher_thershold_ewma_rates
                    else:
                        thershold_intersection_list = list(set(thershold_intersection_list) & set(entry.higher_thershold_ewma_rates))
                        if not thershold_intersection_list:
                            highest_thershold_valid = False
                # It checks if there is a possible intersection among the clients rates for the cur prob.
                if second_thershold_valid is True:
                    # If a given client does not have any rate higher than the required prob (e.g. thershold% for cur prob)
                    # it is assumed that there is no possible intersection
                    if not entry.higher_thershold_cur_prob_rates:
                        second_thershold_valid = False
                    elif not thershold_highest_cur_prob_rate_intersection_list:
                        thershold_highest_cur_prob_rate_intersection_list = entry.higher_thershold_cur_prob_rates
                    else:
                        thershold_highest_cur_prob_rate_intersection_list = list(set(thershold_highest_cur_prob_rate_intersection_list) & set(entry.higher_thershold_cur_prob_rates))
                        if not thershold_highest_cur_prob_rate_intersection_list:
                            second_thershold_valid = False

        # If the old client was the only client in the wtp or there is not any client, lets have the basic rate
        if min_rate == sys.maxsize or min_highest_cur_prob_rate == sys.maxsize:
            for index, entry in enumerate(self.mcast_wtps):
                if entry.block.hwaddr == mcast_wtp.block.hwaddr:
                    min_rate = min(entry.block.supports)
                    min_highest_cur_prob_rate = min(entry.block.supports)
                    break
        
        # If some rates have been obtained as a result of the intersection, the highest one is selected as the rate. 
        if thershold_intersection_list:
            best_rate = max(thershold_intersection_list)
        # Otherwise, the rate selected is the minimum among the MRs
        else:
            best_rate = min_rate
        # The same happens for the cur prob. 
        if thershold_highest_cur_prob_rate_intersection_list:
            best_highest_cur_prob_rate = max(thershold_highest_cur_prob_rate_intersection_list)
        else:
            best_highest_cur_prob_rate = min_highest_cur_prob_rate

        return best_rate, best_highest_cur_prob_rate
    
    def to_dict(self):
        """Return JSON-serializable representation of the object."""
        out = super().to_dict()

        out['mcast_clients'] = []
        for p in self.mcast_clients:
            out['mcast_clients'].append(p.to_dict())
        out['mcast_wtps'] = []
        for p in self.mcast_wtps:
            out['mcast_wtps'].append(p.to_dict())

        return out                                  

def launch(tenant_id, every=50, mcast_clients=[], mcast_wtps=[]):
    """ Initialize the module. """

    return MCastMultigroup(tenant_id=tenant_id, every=every, mcast_clients=mcast_clients, mcast_wtps=mcast_wtps)