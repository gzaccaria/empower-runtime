#!/usr/bin/env python3
#
# Copyright (c) 2017 Estefania Coronado
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the License for the
# specific language governing permissions and limitations
# under the License.

import random
import sys
import time
import os

from empower.core.app import EmpowerApp
from empower.core.app import DEFAULT_PERIOD
from empower.datatypes.etheraddress import EtherAddress
from empower.core.resourcepool import ResourceBlock
from empower.main import RUNTIME
from empower.maps.ucqm import ucqm
from empower.bin_counter.bin_counter import BinCounter
from empower.bin_counter.bin_counter import BinCounterWorker
from empower.events.wtpup import wtpup
from empower.events.wtpdown import wtpdown
from empower.events.lvapjoin import lvapjoin
from empower.events.lvapleave import lvapleave
from empower.lvap_stats.lvap_stats import lvap_stats
from empower.lvap_stats.lvap_stats import LVAPStatsWorker
from empower.core.resourcepool import BANDS
from empower.apps.survey import survey


RSSI_LIMIT = 8
DEFAULT_ADDRESS = "ff:ff:ff:ff:ff:ff"

class WifiLoadBalancing(EmpowerApp):

    def __init__(self, **kwargs):

        EmpowerApp.__init__(self, **kwargs)

        self.test = "test1"

        self.wifi_data = {}
        self.bitrate_data_active = {}

        self.nb_app_active = {}

        self.stations_channels_matrix = {}
        self.stations_aps_matrix = {}

        self.initial_setup = True
        self.warm_up_phases = 20

        self.conflict_aps = {}
        self.aps_channels_matrix = {}
        self.aps_clients_rel = {}
        self.aps_occupancy = {}

        self.coloring_channels  = {"00:0D:B9:3E:05:44": 149, "00:0D:B9:3E:06:9C": 153, "00:0D:B9:3E:D9:DC": 157}

        self.old_aps_occupancy = {}
        self.handover_occupancies = {}
        self.unsuccessful_handovers = {}

        # Register an wtp up event
        self.wtpup(callback=self.wtp_up_callback)

        # Register an lvap join event
        self.lvapjoin(callback=self.lvap_join_callback)

        self.log_file = "/home/estefania/handoverlog.txt"
        self.bin_counters_file = "/home/estefania/bincounterlog.txt"
        self.handovers_counter = 0
        self.handovers_reverted = 0
        self.last_handover_time = None
        self.max_load = 75

    def to_dict(self):
        """Return json-serializable representation of the object."""

        out = super().to_dict()
        out['wifi_data'] = self.wifi_data
        out['aps_clients_rel'] = self.aps_clients_rel
        out['conflict_aps'] = self.conflict_aps
        out['stations_aps_matrix'] = self.stations_aps_matrix
        out['bitrate_data_active'] = self.bitrate_data_active
        out['aps_occupancy'] = self.aps_occupancy
        out['handovers_counter'] = self.handovers_counter
        out['handovers_reverted'] = self.handovers_reverted
        out['handover_occupancies'] = self.handover_occupancies
        out['unsuccessful_handovers'] = self.unsuccessful_handovers
        return out


    def wtp_up_callback(self, wtp):
        """Called when a new WTP connects to the controller."""

        lvaps = RUNTIME.tenants[self.tenant.tenant_id].lvaps

        for block in wtp.supports:
        
            if block.addr.to_str() in self.coloring_channels:
                block.channel = self.coloring_channels[block.addr.to_str()]

            self.ucqm(block=block,
                        tenant_id=self.tenant.tenant_id,
                        every=self.every,
                        callback=self.ucqm_callback)

            self.summary(addr=DEFAULT_ADDRESS,
                         block=block,
                         every=self.every,
                         callback=self.summary_callback)

            self.conflict_aps[block.addr.to_str()] = []
            self.aps_clients_rel[block.addr.to_str()] = []
            self.aps_channels_matrix[block.addr.to_str()] = block.channel
            self.bitrate_data_active[block.addr.to_str()] = {}
            self.nb_app_active[block.addr.to_str()] = 0
            self.aps_occupancy[block.addr.to_str()] = 0


    def lvap_join_callback(self, lvap):
        """Called when an joins the network."""

        self.bin_counter(lvap=lvap.addr,
                 every=1000,
                 callback=self.counters_callback)

        self.lvap_stats(lvap=lvap.addr, 
                    every=1000, 
                    callback=self.lvap_stats_callback)

        if lvap.addr.to_str() not in self.aps_clients_rel[lvap.blocks[0].addr.to_str()]:
            self.aps_clients_rel[lvap.blocks[0].addr.to_str()].append(lvap.addr.to_str())

        self.stations_aps_matrix[lvap.addr.to_str()] = []
        if lvap.blocks[0].addr.to_str() not in self.stations_aps_matrix[lvap.addr.to_str()]:
            self.stations_aps_matrix[lvap.addr.to_str()].append(lvap.blocks[0].addr.to_str())

    def lvap_leave_callback(self, lvap):
        """Called when an LVAP disassociates from a tennant."""

        self.delete_bincounter_worker(lvap)
        self.delete_lvap_stats_worker(lvap)

        if lvap.addr.to_str() in self.aps_clients_rel[lvap.blocks[0].addr.to_str()]:
            self.aps_clients_rel[lvap.blocks[0].addr.to_str()].remove(lvap.addr.to_str())
        if lvap.addr.to_str() in self.bitrate_data_active[lvap.blocks[0].addr.to_str()]:
            del self.bitrate_data_active[lvap.blocks[0].addr.to_str()][lvap.addr.to_str()]
            self.nb_app_active[lvap.blocks[0].addr.to_str()] = len(self.bitrate_data_active[lvap.blocks[0].addr.to_str()])

    def low_rssi(self, trigger):
        """ Perform handover if an LVAP's rssi is
        going below the threshold. """

        self.log.info("Received trigger from %s rssi %u dB",
                      trigger.event['block'],
                      trigger.event['current'])

        lvap = self.lvap(trigger.lvap)

        if not lvap:
            return

        self.evaluate_lvap_revert(lvap)

    def summary_callback(self, summary):
        """ New stats available. """

        self.log.info("New summary from %s addr %s frames %u", summary.block,
                      summary.addr, len(summary.frames))

        # per block log
        filename = "survey_simplerssicombbalancing_%s_%s_%u_%s.csv" % (self.test, summary.block.addr,
                                            summary.block.channel,
                                            BANDS[summary.block.band])

        for frame in summary.frames:

            line = "%u,%g,%s,%d,%u,%s,%s,%s,%s,%s\n" % \
                (frame['tsft'], frame['rate'], frame['rtype'], frame['rssi'],
                 frame['length'], frame['type'], frame['subtype'],
                 frame['ra'], frame['ta'], frame['seq'])

            with open(filename, 'a') as file_d:
                file_d.write(line)

    def lvap_stats_callback(self, counter):
        """ New stats available. """

        rates = (counter.to_dict())["rates"]
        if not rates or counter.lvap not in RUNTIME.lvaps:
            return

        lvap = RUNTIME.lvaps[counter.lvap]
        highest_rate = int(float(max(rates, key=lambda v: int(float(rates[v]['prob'])))))
        key = lvap.blocks[0].addr.to_str() + lvap.addr.to_str()

        if lvap.blocks[0].addr.to_str() not in self.old_aps_occupancy:
            self.old_aps_occupancy[lvap.blocks[0].addr.to_str()] = self.update_occupancy_ratio(lvap.blocks[0])

        # if key in self.wifi_data:
        #     if self.wifi_data[key]['rate'] == 0:
        #         self.wifi_data[key]['rate'] = highest_rate
        #     elif highest_rate != self.wifi_data[key]['rate']:
        #         self.wifi_data[key]['rate_attempts'] += 1
        #         if self.wifi_data[key]['rate_attempts'] < 3:
        #             return
        # else:
        #     self.wifi_data[key] = \
        #     {
        #         'rssi': None,
        #         'wtp': lvap.blocks[0].addr.to_str(),
        #         'sta': lvap.addr.to_str(),
        #         'channel': lvap.blocks[0].channel,
        #         'active': 1,
        #         'tx_bytes_per_second': 0,
        #         'rx_bytes_per_second': 0,
        #         'reesched_attempts': 0,
        #         'revert_attempts': 0,
        #         'rate': highest_rate,
        #         'rate_attempts': 0
        #     }

        if key not in self.wifi_data:
            self.wifi_data[key] = \
            {
                'rssi': None,
                'wtp': lvap.blocks[0].addr.to_str(),
                'sta': lvap.addr.to_str(),
                'channel': lvap.blocks[0].channel,
                'active': 1,
                'tx_bytes_per_second': 0,
                'rx_bytes_per_second': 0,
                'reesched_attempts': 0,
                'revert_attempts': 0,
                'rate': highest_rate,
                'rate_attempts': 0
            }

        self.wifi_data[key]['rate'] = highest_rate
        self.wifi_data[key]['rate_attempts'] = 0
        
        new_occupancy = self.update_occupancy_ratio(lvap.blocks[0])
        # average_occupancy = self.average_occupancy_surrounding_aps(lvap)
        average_occupancy = self.estimate_global_occupancy_ratio()

        # print("counters")
        # print("------self.bitrate_data_active[block]", self.bitrate_data_active[lvap.blocks[0].addr.to_str()])
        # print("------Revert attempts: ", self.wifi_data[key]['revert_attempts'])
        # print("------Reesched attempts: ", self.wifi_data[key]['reesched_attempts'])
        # print("------New occupancy: ", new_occupancy)
        # print("------self.old_aps_occupancy[block.addr.to_str()]: ", self.old_aps_occupancy[lvap.blocks[0].addr.to_str()])
        # print("------average_occupancy: ", average_occupancy)

        #if new_occupancy != average_occupancy:
        # if new_occupancy < (average_occupancy * 0.975) or new_occupancy > (average_occupancy * 1.025) or \
        # new_occupancy < (self.old_aps_occupancy[lvap.blocks[0].addr.to_str()] * 0.975) or \
        # new_occupancy > (self.old_aps_occupancy[lvap.blocks[0].addr.to_str()] * 1.025):
        if (self.last_handover_time is not None and (time.time() - self.last_handover_time) < 5) \
            or len(self.handover_occupancies) != 0:
            return

        if self.evalute_significant_occupancy_dif(self.old_aps_occupancy[lvap.blocks[0].addr.to_str()], new_occupancy, average_occupancy) is True:
            self.old_aps_occupancy[lvap.blocks[0].addr.to_str()] = new_occupancy
            if lvap not in self.handover_occupancies:
                self.evaluate_lvap_scheduling(lvap)

    def counters_callback(self, stats):
        """ New stats available. """

        self.log.info("New counters received from %s" % stats.lvap)
        print("stats.rx_bytes_per_second", stats.rx_bytes_per_second)
        print("stats.tx_bytes_per_second", stats.tx_bytes_per_second)
        print(stats.tx_bytes)
        print(stats.rx_bytes)

        lvap = RUNTIME.lvaps[stats.lvap]
        block = lvap.blocks[0]

        if os.path.isfile(self.bin_counters_file):
            fh = open(self.bin_counters_file,"a")
        else:
            fh = open(self.bin_counters_file,"w")
        print("sta %s stats.rx_bytes %s" %(stats.lvap, stats.rx_bytes), file=fh)
        fh.close()

        # print("---------+++++++++++++++++++----------------++++++++++")
        # print("---------+++++++++++++++++++----------------++++++++++")
        # print("Counters from %s block %s" %(lvap.addr.to_str(), block.addr.to_str()))
        # print("tx %f rx %f" %(stats.tx_bytes_per_second[0], stats.rx_bytes_per_second[0]))
        # print("---------+++++++++++++++++++----------------++++++++++")
        # print("---------+++++++++++++++++++----------------++++++++++")

        if (not stats.tx_bytes_per_second and not stats.rx_bytes_per_second) and \
            (block.addr.to_str() + stats.lvap.to_str() not in self.wifi_data):
            return

        if not stats.tx_bytes_per_second:
            stats.tx_bytes_per_second = []
            stats.tx_bytes_per_second.append(0)
        if not stats.rx_bytes_per_second:
            stats.rx_bytes_per_second = []
            stats.rx_bytes_per_second.append(0)

        self.counters_to_file(lvap, block, stats)

        key = block.addr.to_str() + stats.lvap.to_str()
        if block.addr.to_str() not in self.old_aps_occupancy or self.old_aps_occupancy[block.addr.to_str()] == 0:
            self.old_aps_occupancy[block.addr.to_str()] = self.update_occupancy_ratio(block)

        if key in self.wifi_data:
            self.wifi_data[key]['tx_bytes_per_second'] = stats.tx_bytes_per_second[0]
            self.wifi_data[key]['rx_bytes_per_second'] = stats.rx_bytes_per_second[0]
        else:
            self.wifi_data[block.addr.to_str() + stats.lvap.to_str()] = \
            {
                'rssi': None,
                'wtp': block.addr.to_str(),
                'sta': stats.lvap.to_str(),
                'channel': lvap.blocks[0].channel,
                'active': 1,
                'tx_bytes_per_second': stats.tx_bytes_per_second[0],
                'rx_bytes_per_second': stats.rx_bytes_per_second[0],
                'reesched_attempts': 0,
                'revert_attempts': 0,
                'rate': 0,
                'rate_attempts': 0
            }
                            
        # Minimum voice bitrates:
        # https://books.google.it/books?id=ExeKR1iI8RgC&pg=PA88&lpg=PA88&dq=bandwidth+consumption+per+application+voice+video+background&source=bl&ots=1zUvCgqAhZ&sig=5kkM447M4t9ezbVDde3-D3oh2ww&hl=it&sa=X&ved=0ahUKEwiRuvOJv6vUAhWPDBoKHYd5AysQ6AEIWDAG#v=onepage&q=bandwidth%20consumption%20per%20application%20voice%20video%20background&f=false
        # https://www.voip-info.org/wiki/view/Bandwidth+consumption
        # G729A codec minimum bitrate 17K 17804
        if lvap.addr.to_str() not in self.bitrate_data_active[block.addr.to_str()]:
            self.bitrate_data_active[block.addr.to_str()][lvap.addr.to_str()] = \
                                            {
                                                'tx_bytes_per_second': 0,
                                                'rx_bytes_per_second': 0
                                            }

        if stats.tx_bytes_per_second[0] >= 500:
            self.bitrate_data_active[block.addr.to_str()][lvap.addr.to_str()]['tx_bytes_per_second'] = stats.tx_bytes_per_second[0]
        else:
            self.bitrate_data_active[block.addr.to_str()][lvap.addr.to_str()]['tx_bytes_per_second'] = 0

        if stats.rx_bytes_per_second[0] >= 500:
            self.bitrate_data_active[block.addr.to_str()][lvap.addr.to_str()]['rx_bytes_per_second'] = stats.rx_bytes_per_second[0]
        else:
            self.bitrate_data_active[block.addr.to_str()][lvap.addr.to_str()]['rx_bytes_per_second'] = 0       

        if (stats.rx_bytes_per_second[0] < 500) and (stats.tx_bytes_per_second[0] < 500) and len(self.stations_aps_matrix[lvap.addr.to_str()]) > 1:
            self.wifi_data[key]['revert_attempts'] += 1

        new_occupancy = self.update_occupancy_ratio(block)
        # average_occupancy = self.average_occupancy_surrounding_aps(lvap)
        average_occupancy = self.estimate_global_occupancy_ratio()
        print("self.old_aps_occupancy[block.addr.to_str()] ", self.old_aps_occupancy[block.addr.to_str()])

        #if new_occupancy != average_occupancy:
        # if new_occupancy < (average_occupancy * 0.975) or new_occupancy > (average_occupancy * 1.025) or \
        # new_occupancy < (self.old_aps_occupancy[block.addr.to_str()] * 0.975) or \
        # new_occupancy > (self.old_aps_occupancy[block.addr.to_str()] * 1.025):
        old_occupancy = self.old_aps_occupancy[block.addr.to_str()]
        if self.evalute_significant_occupancy_dif(old_occupancy, new_occupancy, average_occupancy) is True:
            if len(self.stations_aps_matrix[lvap.addr.to_str()]) > 1:
                self.wifi_data[key]['reesched_attempts'] += 1

        self.nb_app_active[block.addr.to_str()] = len(self.bitrate_data_active[block.addr.to_str()])

        # print("------self.bitrate_data_active[block]", self.bitrate_data_active[block.addr.to_str()])
        # print("------Revert attempts: ", self.wifi_data[key]['revert_attempts'])
        # print("------Reesched attempts: ", self.wifi_data[key]['reesched_attempts'])
        # print("------New occupancy: ", new_occupancy)
        # print("------self.old_aps_occupancy[block.addr.to_str()]: ", self.old_aps_occupancy[block.addr.to_str()])
        # print("------average_occupancy: ", average_occupancy)


        if (self.last_handover_time is not None and (time.time() - self.last_handover_time) < 5) \
            or len(self.handover_occupancies) != 0:
            return

        # if self.wifi_data[key]['revert_attempts'] >= 3:
        if self.wifi_data[key]['revert_attempts'] >= 1:
            if lvap.addr.to_str() in self.bitrate_data_active[block.addr.to_str()]:
                del self.bitrate_data_active[block.addr.to_str()][lvap.addr.to_str()]
                self.nb_app_active[block.addr.to_str()] = len(self.bitrate_data_active[block.addr.to_str()])
            self.wifi_data[key]['revert_attempts'] = 0
            if lvap not in self.handover_occupancies:
                self.evaluate_lvap_revert(lvap)
        elif self.wifi_data[key]['reesched_attempts'] >= 3:
            self.wifi_data[key]['reesched_attempts'] = 0
            self.old_aps_occupancy[block.addr.to_str()] = new_occupancy
            #if self.nb_app_active[block.addr.to_str()] > 1:
            if lvap not in self.handover_occupancies:
                self.evaluate_lvap_scheduling(lvap)

    def counters_to_file(self, lvap, block, stats):
        """ New stats available. """

        # per block log
        filename = "simplerssicombbalancing_%s_%s_%u_%s.csv" % (self.test, block.addr.to_str(),
                                            block.channel,
                                            BANDS[block.band])


        line = "%f,%s,%s,%u,%f, %f,%f\n" % \
            (stats.last, lvap.addr.to_str(), block.addr.to_str(), block.channel, self.aps_occupancy[block.addr.to_str()], \
             stats.rx_bytes_per_second[0], stats.tx_bytes_per_second[0])

        with open(filename, 'a') as file_d:
            file_d.write(line)

    def update_occupancy_ratio(self, block):
        
        if block.addr.to_str() not in self.aps_clients_rel:
            self.aps_occupancy[block.addr.to_str()] = 0
            return 0
        if self.aps_clients_rel[block.addr.to_str()] is None:
            self.aps_occupancy[block.addr.to_str()] = 0
            return 0

        occupancy = 0
        for sta in self.aps_clients_rel[block.addr.to_str()]:
            if block.addr.to_str() + sta not in self.wifi_data:
                continue
            
            if self.wifi_data[block.addr.to_str() + sta]['tx_bytes_per_second'] == 0 and \
                self.wifi_data[block.addr.to_str() + sta]['rx_bytes_per_second'] == 0:
                continue

            if self.wifi_data[block.addr.to_str() + sta]['rate'] == 0:
                continue

            occupancy += ((((self.wifi_data[block.addr.to_str() + sta]['tx_bytes_per_second'] \
                            + self.wifi_data[block.addr.to_str() + sta]['rx_bytes_per_second']) * 8) \
                            / self.wifi_data[block.addr.to_str() + sta]['rate']) / 1000000)*100

        # print("/**/*/*/*/*/*/*/* Occupancy ratio of block %s is %d" %(block.addr.to_str(), occupancy))
        self.aps_occupancy[block.addr.to_str()] = occupancy
        return occupancy

    def estimate_global_occupancy_ratio(self):

        global_occupancy = 0
        for ratio in self.aps_occupancy.values():
            global_occupancy += ratio
        
        return (global_occupancy/len(self.aps_occupancy))


    def evaluate_lvap_revert(self, lvap):

        block = lvap.blocks[0]

        if block.addr.to_str() + lvap.addr.to_str() not in self.wifi_data or \
           self.wifi_data[block.addr.to_str() + lvap.addr.to_str()]['rssi'] is None:
           return

        if lvap.addr.to_str() not in self.stations_aps_matrix:
            return

        current_rssi = self.wifi_data[block.addr.to_str() + lvap.addr.to_str()]['rssi']
        best_rssi = -120
        new_block = None
        
        for wtp in self.stations_aps_matrix[lvap.addr.to_str()]:
            if wtp == block.addr.to_str():
                continue
            if self.wifi_data[wtp + lvap.addr.to_str()]['rssi'] <= (current_rssi + RSSI_LIMIT) or \
                self.wifi_data[wtp + lvap.addr.to_str()]['rssi'] < best_rssi or self.wifi_data[wtp + lvap.addr.to_str()]['rssi'] == 0:
                continue

            best_rssi = self.wifi_data[wtp + lvap.addr.to_str()]['rssi']
            new_block = self.get_block_for_ap_addr(wtp)

        if not new_block:
            return

        if lvap.blocks[0] == new_block:
            return 

        try:
            lvap.blocks = new_block
            self.handovers_counter += 1
            self.last_handover_time = time.time()

            print("++++++++ Transfering inactive LVAP from %s to %s++++++++" %(block.addr.to_str(), new_block.addr.to_str()))
            print("current_rssi %d. Target rssi %d" % (current_rssi, best_rssi))

            if os.path.isfile(self.log_file):
                fh = open(self.log_file,"a")
            else:
                fh = open(self.log_file,"w")
            print("++++++++ Transfering inactive LVAP from %s to %s++++++++" %(block.addr.to_str(), new_block.addr.to_str()), file=fh)
            print("current_rssi %d. Target rssi %d" % (current_rssi, best_rssi), file=fh)
            # fh.close()

            self.transfer_block_data(block, new_block, lvap)

            self.nb_app_active[block.addr.to_str()] = len(self.bitrate_data_active[block.addr.to_str()])
            self.update_occupancy_ratio(block)

            self.nb_app_active[new_block.addr.to_str()] = len(self.bitrate_data_active[new_block.addr.to_str()])
            self.update_occupancy_ratio(new_block)

            print("New occupancy of source block %s (occup. %f) and dest block %s (occup. %f)" %(block.addr.to_str(), self.aps_occupancy[block.addr.to_str()], \
                new_block.addr.to_str(), self.aps_occupancy[new_block.addr.to_str()]), file=fh)

            print("wifi data src block %s" %(block.addr.to_str()), file=fh)
            for key, clients in self.aps_clients_rel.items():
                for client in clients:
                    print(self.wifi_data[block.addr.to_str()+client], file=fh)
            print("wifi data dst block %s" %(new_block.addr.to_str()), file=fh)
            for key, clients in self.aps_clients_rel.items():
                for client in clients:
                    print(self.wifi_data[new_block.addr.to_str()+client], file=fh)
            fh.close()
        except ValueError:
            print("Handover already in progress for lvap %s" % lvap.addr.to_str())
            return


    def evaluate_lvap_scheduling(self, lvap):

        block = lvap.blocks[0]

        # It is not necessary to perform a change if the traffic of the ap is lower than the average or if it is holding a single lvap
        if block.addr.to_str() not in self.aps_occupancy:
            return

        # average_occupancy = self.average_occupancy_surrounding_aps(lvap)
        average_occupancy = self.estimate_global_occupancy_ratio()
        new_block = None
        clients_candidates = {}

        if os.path.isfile(self.log_file):
            fh = open(self.log_file,"a")
        else:
            fh = open(self.log_file,"w")

        print("/////////////// Evaluating reescheduling in block %s ///////////////" % block.addr.to_str())
        print("average_occupancy", average_occupancy)
        print("self.aps_occupancy[block.addr.to_str()]", self.aps_occupancy[block.addr.to_str()])
        print("/////////////// Evaluating reescheduling in block %s ///////////////" % block.addr.to_str(), file=fh)
        print("average_occupancy", average_occupancy, file=fh)
        print("self.aps_occupancy[block.addr.to_str()]", self.aps_occupancy[block.addr.to_str()], file=fh)
        if self.aps_occupancy[block.addr.to_str()] <= average_occupancy or self.nb_app_active[block.addr.to_str()] < 2:
            return

        ########## Look for the lvaps from this wtp that can be reescheduled ###########
        clients_candidates = {}

        for sta in self.aps_clients_rel[block.addr.to_str()]:
            print("----> Station %s" % sta, file=fh)
            # print("Evaluating sta %s" % sta)
            # If this station has no other candidates, it is discarded
            if sta not in self.stations_aps_matrix or len(self.stations_aps_matrix[sta]) < 2:
                print("      Less than 2 APs ", self.stations_aps_matrix[sta], file=fh)
                continue

            sta_lvap = self.get_lvap_for_sta_addr(sta)
            if sta_lvap in self.handover_occupancies:
                print("      In handover occup ", self.handover_occupancies, file=fh)
                continue

            # Check the wtps that this lvap have in the signal graph
            # print("APs for sta %s" % sta)
            # print(self.stations_aps_matrix[sta])
            
            for wtp in self.stations_aps_matrix[sta]:
                print("              * AP candidate %s occupancy %f RSSI sta-wtp %d" % (wtp, self.aps_occupancy[wtp], self.wifi_data[wtp + sta]['rssi']), file=fh)
                #TODO. ADD THRES. WHEN THE UNITS OF THE OCCUPANCY ARE KNOWN
                if wtp == block.addr.to_str():
                    continue
                # print("Candidate %s occupancy %f" %(wtp, self.aps_occupancy[wtp]))
                if self.aps_occupancy[wtp] > self.aps_occupancy[block.addr.to_str()] \
                    or self.wifi_data[wtp + sta]['rssi'] < -85:
                    continue

                # Checks if a similar handover has been performed in an appropiate way.
                # If the conditions have changed for 5 times in a row, the wtp is taken again as a candidate
                if sta in self.unsuccessful_handovers and wtp in self.unsuccessful_handovers[sta]:
                    # if block.addr.to_str() == self.unsuccessful_handovers[sta][wtp]['old_ap'] and \
                    # self.aps_occupancy[wtp] < (self.unsuccessful_handovers[sta][wtp]['previous_occupancy'] * 0.975):
                    if self.evalute_significant_occupancy_dif(self.unsuccessful_handovers[sta][wtp]['previous_occupancy'], \
                        self.aps_occupancy[wtp], self.unsuccessful_handovers[sta][wtp]['previous_occupancy']) is True:
                    # self.aps_occupancy[wtp] != self.unsuccessful_handovers[sta][wtp]['previous_occupancy']:
                        self.unsuccessful_handovers[sta][wtp]['handover_retries'] += 1
                    if self.unsuccessful_handovers[sta][wtp]['handover_retries'] < 5:
                        continue
                    del self.unsuccessful_handovers[sta][wtp]

                conflict_occupancy = self.aps_occupancy[wtp]
                wtp_channel = self.aps_channels_matrix[wtp]
                if wtp in self.conflict_aps:
                    for neigh in self.conflict_aps[wtp]:
                        if self.aps_channels_matrix[neigh] != wtp_channel:
                            continue 
                        conflict_occupancy += self.aps_occupancy[neigh]

                wtp_info = \
                    {
                        'wtp': wtp,
                        'metric' : abs(self.wifi_data[wtp + sta]['rssi']) * self.aps_occupancy[wtp],
                        'conf_occupancy': conflict_occupancy,
                        'conf_metric': abs(self.wifi_data[wtp + sta]['rssi']) * conflict_occupancy,
                        'rssi': self.wifi_data[wtp + sta]['rssi']
                    }
                if sta not in clients_candidates:
                    clients_candidates[sta] = []
                clients_candidates[sta].append(wtp_info)
            
            # if len(clients_candidates[sta]) == 0:
            #     del clients_candidates[sta]
        fh.close()

        if len(clients_candidates) == 0:
            # print("Not possible reescheduling. The network is balanced")
            return

        # print("Final candidates relationship")
        print(clients_candidates)

        ########## Evaluate list of candidates lvaps-wtsp ###########
        highest_metric = sys.maxsize
        best_wtp = None
        best_lvap = None
        best_rssi = -120
        global_occupancy_before_ho = self.estimate_global_occupancy_ratio()

        if global_occupancy_before_ho <= self.max_load:
            for sta, wtps in clients_candidates.items():
                for ap in wtps:
                    if ap['metric'] < highest_metric and ap['conf_metric'] < highest_metric:
                        highest_metric = ap['conf_metric']
                        best_wtp = ap['wtp']
                        best_lvap = sta
                    # In case of finding 2 candidates lvaps whose target WTPs occupancy is the same, we will take the one
                    # whose current wtp occupancy is higher. In that case it will be less crowded after the handover
                    elif ap['metric'] == highest_metric and ap['conf_metric'] == highest_metric:
                        if self.aps_occupancy[ap['wtp']] > self.aps_occupancy[best_wtp]:
                            best_wtp = ap['wtp']
                            best_lvap = sta
        else:
            for sta, wtps in clients_candidates.items():
                for ap in wtps:
                    if ap['rssi'] > best_rssi and ap['rssi'] != 0:
                        best_rssi = ap['rssi']
                        best_wtp = ap['wtp']
                        best_lvap = sta
                    # In case of finding 2 candidates lvaps whose target WTPs occupancy is the same, we will take the one
                    # whose current wtp occupancy is higher. In that case it will be less crowded after the handover
                    elif ap['rssi'] == best_rssi:
                        if self.aps_occupancy[ap['wtp']] > self.aps_occupancy[best_wtp]:
                            best_wtp = ap['wtp']
                            best_lvap = sta

        new_block = self.get_block_for_ap_addr(best_wtp)
        new_lvap = self.get_lvap_for_sta_addr(best_lvap)

        if new_block is None or new_lvap is None:
            # print("KDSFJLDSJFLKDSFJKLDSFJLKDSFDFJDSLKFJDKSL9999999999999999999999 NOT NEW BLOCK")
            return

        if new_lvap.blocks[0] == new_block:
            return 

        try:
            src_block = new_lvap.blocks[0].addr.to_str()
            new_lvap.blocks = new_block

            self.handovers_counter += 1
            self.last_handover_time = time.time()

            current_metric = abs(self.wifi_data[src_block + new_lvap.addr.to_str()]['rssi']) * self.aps_occupancy[src_block]
            new_metric = abs(self.wifi_data[new_block.addr.to_str() + new_lvap.addr.to_str()]['rssi']) * self.aps_occupancy[new_block.addr.to_str()]
            print("/////////////// Performing handover for LVAP %s ///////////////" % new_lvap.addr.to_str())
            print("Handover from %s (occup. %f - metric %f) to %s (occup. %f - metric %f)" %(src_block, self.aps_occupancy[src_block], \
                current_metric, new_block.addr.to_str(), self.aps_occupancy[new_block.addr.to_str()], new_metric))

            if os.path.isfile(self.log_file):
                fh = open(self.log_file,"a")
            else:
                fh = open(self.log_file,"w")
            print("/////////////// Performing handover for LVAP %s ///////////////" % new_lvap.addr.to_str(), file=fh)
            print("Handover from %s (occup. %f - metric %f) to %s (occup. %f - metric %f)" %(src_block, self.aps_occupancy[src_block], \
                current_metric, new_block.addr.to_str(), self.aps_occupancy[new_block.addr.to_str()], new_metric), file=fh)
            # fh.close()

            self.handover_occupancies[new_lvap] = \
                {
                    'old_ap': block.addr.to_str(),
                    'handover_ap': best_wtp,
                    'previous_occupancy': global_occupancy_before_ho,
                    'handover_time': time.time()
                }
        
            self.transfer_block_data(block, new_block, new_lvap)

            self.nb_app_active[block.addr.to_str()] = len(self.bitrate_data_active[block.addr.to_str()])
            self.update_occupancy_ratio(block)            

            self.nb_app_active[new_block.addr.to_str()] = len(self.bitrate_data_active[new_block.addr.to_str()])
            self.update_occupancy_ratio(new_block)

            print("New occupancy of source block %s (occup. %f) and dest block %s (occup. %f)" %(src_block, self.aps_occupancy[src_block], \
                new_block.addr.to_str(), self.aps_occupancy[new_block.addr.to_str()]), file=fh)

            print("wifi data src block %s" %(src_block), file=fh)
            for key, clients in self.aps_clients_rel.items():
                for client in clients:
                    print(self.wifi_data[src_block+client], file=fh)
            print("wifi data dst block %s" %(new_block.addr.to_str()), file=fh)
            for key, clients in self.aps_clients_rel.items():
                for client in clients:
                    print(self.wifi_data[new_block.addr.to_str()+client], file=fh)
            fh.close()

        except ValueError:
            print("Handover already in progress for lvap %s" % lvap.addr.to_str())
            return


    def transfer_block_data(self, src_block, dst_block, lvap):

        if lvap.addr.to_str() in self.aps_clients_rel[src_block.addr.to_str()]:
            self.aps_clients_rel[src_block.addr.to_str()].remove(lvap.addr.to_str())
        if lvap.addr.to_str() not in self.aps_clients_rel[dst_block.addr.to_str()]:
            self.aps_clients_rel[dst_block.addr.to_str()].append(lvap.addr.to_str())

        self.wifi_data[dst_block.addr.to_str() + lvap.addr.to_str()]['tx_bytes_per_second'] = self.wifi_data[src_block.addr.to_str() + lvap.addr.to_str()]['tx_bytes_per_second']
        self.wifi_data[dst_block.addr.to_str() + lvap.addr.to_str()]['rx_bytes_per_second'] = self.wifi_data[src_block.addr.to_str() + lvap.addr.to_str()]['rx_bytes_per_second']

        if (src_block.addr.to_str() + lvap.addr.to_str()) in self.wifi_data:
            self.wifi_data[src_block.addr.to_str() + lvap.addr.to_str()]['tx_bytes_per_second'] = 0
            self.wifi_data[src_block.addr.to_str() + lvap.addr.to_str()]['rx_bytes_per_second'] = 0
            self.wifi_data[src_block.addr.to_str() + lvap.addr.to_str()]['reesched_attempts'] = 0
            self.wifi_data[src_block.addr.to_str() + lvap.addr.to_str()]['revert_attempts'] = 0
            self.wifi_data[src_block.addr.to_str() + lvap.addr.to_str()]['rate'] = 0
            self.wifi_data[src_block.addr.to_str() + lvap.addr.to_str()]['rate_attempts'] = 0
            self.wifi_data[src_block.addr.to_str() + lvap.addr.to_str()]['active'] = 0

        if src_block.addr.to_str() not in self.bitrate_data_active or \
            lvap.addr.to_str() not in self.bitrate_data_active[src_block.addr.to_str()]:
            return

        if lvap.addr.to_str() not in self.bitrate_data_active[dst_block.addr.to_str()]:
            self.bitrate_data_active[dst_block.addr.to_str()][lvap.addr.to_str()] = \
                {
                    'tx_bytes_per_second': self.bitrate_data_active[src_block.addr.to_str()][lvap.addr.to_str()]['tx_bytes_per_second'],
                    'rx_bytes_per_second': self.bitrate_data_active[src_block.addr.to_str()][lvap.addr.to_str()]['rx_bytes_per_second']
                }
        else:
            self.bitrate_data_active[dst_block.addr.to_str()][lvap.addr.to_str()]['tx_bytes_per_second'] = self.bitrate_data_active[src_block.addr.to_str()][lvap.addr.to_str()]['tx_bytes_per_second']
            self.bitrate_data_active[dst_block.addr.to_str()][lvap.addr.to_str()]['rx_bytes_per_second'] = self.bitrate_data_active[src_block.addr.to_str()][lvap.addr.to_str()]['rx_bytes_per_second']

        del self.bitrate_data_active[src_block.addr.to_str()][lvap.addr.to_str()]


    def conflict_graph(self):

        initial_conflict_graph = self.conflict_aps

        for wtp_list in self.stations_aps_matrix.values():
            for wtp in wtp_list:
                for conflict_wtp in wtp_list:
                    if conflict_wtp != wtp and (conflict_wtp not in self.conflict_aps[wtp]):
                        self.conflict_aps[wtp].append(conflict_wtp)

    def ucqm_callback(self, poller):
        """Called when a UCQM response is received from a WTP."""

        lvaps = RUNTIME.tenants[self.tenant.tenant_id].lvaps

        for addr in poller.maps.values():
            # This means that this lvap is attached to a WTP in the network.
            if addr['addr'] in lvaps and lvaps[addr['addr']].wtp:
                active_flag = 1

                if (lvaps[addr['addr']].wtp.addr != poller.block.addr):
                    active_flag = 0
                elif ((lvaps[addr['addr']].wtp.addr == poller.block.addr and (lvaps[addr['addr']].association_state == False))):
                    active_flag = 0

                if poller.block.addr.to_str() + addr['addr'].to_str() in self.wifi_data:
                    self.wifi_data[poller.block.addr.to_str() + addr['addr'].to_str()]['rssi'] = addr['mov_rssi']
                    self.wifi_data[poller.block.addr.to_str() + addr['addr'].to_str()]['channel'] = poller.block.channel
                    self.wifi_data[poller.block.addr.to_str() + addr['addr'].to_str()]['active'] = active_flag
                else:
                    self.wifi_data[poller.block.addr.to_str() + addr['addr'].to_str()] = \
                                    {
                                        'rssi': addr['mov_rssi'],
                                        'wtp': poller.block.addr.to_str(),
                                        'sta': addr['addr'].to_str(),
                                        'channel': poller.block.channel,
                                        'active': active_flag,
                                        'tx_bytes_per_second': 0,
                                        'rx_bytes_per_second': 0,
                                        'reesched_attempts': 0,
                                        'revert_attempts': 0,
                                        'rate': 0,
                                        'rate_attempts': 0
                                    }

                # Conversion of the data structure to obtain the conflict APs
                if addr['addr'].to_str() not in self.stations_aps_matrix:
                    self.stations_aps_matrix[addr['addr'].to_str()] = []
                if poller.block.addr.to_str() not in self.stations_aps_matrix[addr['addr'].to_str()]:
                    self.stations_aps_matrix[addr['addr'].to_str()].append(poller.block.addr.to_str())

            elif poller.block.addr.to_str() + addr['addr'].to_str() in self.wifi_data:
                del self.wifi_data[poller.block.addr.to_str() + addr['addr'].to_str()]

        self.conflict_graph()

    def average_occupancy_surrounding_aps(self, lvap):
        # average_occupancy = 0

        # for key, wtp in enumerate(self.stations_aps_matrix[lvap.addr.to_str()]):
        #     if wtp not in self.aps_occupancy:
        #         continue
        #     average_occupancy += self.aps_occupancy[wtp]

        # return (average_occupancy / len(self.stations_aps_matrix[lvap.addr.to_str()]))
        average_occupancy = 0
        block = lvap.blocks[0]

        if block.addr.to_str() not in self.conflict_aps:
            #return self.aps_occupancy[block.addr.to_str()]
            return self.estimate_global_occupancy_ratio()
        if len(self.conflict_aps[block.addr.to_str()]) == 0:
            return self.estimate_global_occupancy_ratio()


        for wtp in self.conflict_aps[block.addr.to_str()]:
            if wtp not in self.aps_occupancy:
                continue
            average_occupancy += self.aps_occupancy[wtp]

        average_occupancy += self.aps_occupancy[block.addr.to_str()]

        return (average_occupancy / (len(self.conflict_aps[block.addr.to_str()]) + 1))


    def get_block_for_ap_addr(self, addr):
        wtps = RUNTIME.tenants[self.tenant.tenant_id].wtps
        for wtp in wtps.values():
            for block in wtp.supports:
                if block.addr.to_str() != addr:
                    continue
                return block

        return None

    def get_lvap_for_sta_addr(self, addr):
        lvaps = RUNTIME.tenants[self.tenant.tenant_id].lvaps
        for lvap in lvaps.values():
                if lvap.addr.to_str() != addr:
                    continue
                return lvap

        return None

    def evaluate_handover(self):

        # If a handover has been recently performed. Let's evaluate the new occupancy rate.
        checked_clients = []

        for lvap, value in self.handover_occupancies.items():

            # Wait some time to get statistics before checking if the handover was valid
            if (time.time() - value['handover_time']) < 5:
                continue
            handover_occupancy_rate = self.estimate_global_occupancy_ratio()

            # If the previous occupancy rate was better, the handover must be reverted
            if value['previous_occupancy'] < handover_occupancy_rate and (handover_occupancy_rate - value['previous_occupancy']) > 1:
                self.log.info("The handover from the AP %s to the AP %s for the client %s IS NOT efficient. The previous channel occupancy rate was %f(ms) and it is %f(ms) after the handover. It is going to be reverted" \
                    %(value['old_ap'], value['handover_ap'], lvap, value['previous_occupancy'], handover_occupancy_rate))
                if os.path.isfile(self.log_file):
                    fh = open(self.log_file,"a")
                else:
                    fh = open(self.log_file,"w")
                print("The handover from the AP %s to the AP %s for the client %s IS NOT efficient. The previous channel occupancy rate was %f(ms) and it is %f(ms) after the handover. It is going to be reverted" \
                    %(value['old_ap'], value['handover_ap'], lvap, value['previous_occupancy'], handover_occupancy_rate), file=fh)
                fh.close() 

                self.revert_handover(lvap, handover_occupancy_rate)
            else:
                self.log.info("The handover from the AP %s to the AP %s for the client %s is efficient. The previous channel occupancy rate was %f(ms) and it is %f(ms) after the handover" \
                    %(value['old_ap'], value['handover_ap'], lvap, value['previous_occupancy'], handover_occupancy_rate)) 

            checked_clients.append(lvap)

        for entry in checked_clients:
            del self.handover_occupancies[entry]


    def revert_handover(self, lvap, handover_occupancy_rate):

        handover_ap = self.get_block_for_ap_addr(self.handover_occupancies[lvap]['handover_ap'])
        old_ap = self.get_block_for_ap_addr(self.handover_occupancies[lvap]['old_ap'])

        if lvap.blocks[0] == old_ap:
            return

        try:
            lvap.blocks = old_ap
            self.last_handover_time = time.time()
            self.handovers_reverted += 1

            print("------------------------ Reverting handover from %s to %s" %(handover_ap.addr.to_str(), old_ap.addr.to_str()))

            if os.path.isfile(self.log_file):
                fh = open(self.log_file,"a")
            else:
                fh = open(self.log_file,"w")
            print("------------------------ Reverting handover from %s to %s" %(handover_ap.addr.to_str(), old_ap.addr.to_str()), file=fh)
            # fh.close() 

            if lvap.addr.to_str() not in self.unsuccessful_handovers:
                self.unsuccessful_handovers[lvap.addr.to_str()] = {}

            if handover_ap.addr.to_str() not in self.unsuccessful_handovers[lvap.addr.to_str()]:
                self.unsuccessful_handovers[lvap.addr.to_str()] = \
                    {
                        handover_ap.addr.to_str(): {
                            'rssi': self.wifi_data[handover_ap.addr.to_str() + lvap.addr.to_str()]['rssi'],
                            'previous_occupancy': handover_occupancy_rate,
                            'handover_retries': 0,
                            'old_ap': old_ap.addr.to_str(),
                            'handover_ap': handover_ap.addr.to_str()
                        }
                    }
            else:
                self.unsuccessful_handovers[lvap.addr.to_str()][handover_ap.addr.to_str()]['rssi'] = self.wifi_data[handover_ap.addr.to_str() + lvap.addr.to_str()]['rssi']
                self.unsuccessful_handovers[lvap.addr.to_str()][handover_ap.addr.to_str()]['previous_occupancy'] = handover_occupancy_rate
                self.unsuccessful_handovers[lvap.addr.to_str()][handover_ap.addr.to_str()]['handover_retries'] = 0
                self.unsuccessful_handovers[lvap.addr.to_str()][handover_ap.addr.to_str()]['old_ap'] = old_ap.addr.to_str()
                self.unsuccessful_handovers[lvap.addr.to_str()][handover_ap.addr.to_str()]['handover_ap'] = handover_ap.addr.to_str()

            self.transfer_block_data(handover_ap, old_ap, lvap)

            self.nb_app_active[handover_ap.addr.to_str()] = len(self.bitrate_data_active[handover_ap.addr.to_str()])
            self.update_occupancy_ratio(handover_ap)

            self.nb_app_active[old_ap.addr.to_str()] = len(self.bitrate_data_active[old_ap.addr.to_str()])
            self.update_occupancy_ratio(old_ap)

            print("New occupancy of source block %s (occup. %f) and dest block %s (occup. %f)" %(handover_ap.addr.to_str(), self.aps_occupancy[handover_ap.addr.to_str()], \
                old_ap.addr.to_str(), self.aps_occupancy[old_ap.addr.to_str()]), file=fh)

            print("wifi data src block %s" %(handover_ap.addr.to_str()), file=fh)
            for key, clients in self.aps_clients_rel.items():
                for client in clients:
                    print(self.wifi_data[handover_ap.addr.to_str()+client], file=fh)
            print("wifi data dst block %s" %(old_ap.addr.to_str()), file=fh)
            for key, clients in self.aps_clients_rel.items():
                for client in clients:
                    print(self.wifi_data[old_ap.addr.to_str()+client], file=fh)
            fh.close()

        except ValueError:
            print("Handover already in progress for lvap %s" % lvap.addr.to_str())
            return

    def evalute_significant_occupancy_dif(self, old_occupancy, new_occupancy, average_occupancy):
        # if abs(old_occupancy - new_occupancy) <= 1 and abs(average_occupancy - new_occupancy) <= 1:
        #     return False

        if new_occupancy <= 1:
            return False
        
        elif new_occupancy > 1 or new_occupancy <= 5:
            if new_occupancy < (average_occupancy * 0.5) or new_occupancy > (average_occupancy * 1.5) or \
                new_occupancy < (old_occupancy * 0.5) or new_occupancy > (old_occupancy * 1.5):
                return True
            return False
        elif new_occupancy > 5 or new_occupancy <= 10:
            if new_occupancy < (average_occupancy * 0.75) or new_occupancy > (average_occupancy * 1.25) or \
                new_occupancy < (old_occupancy * 0.75) or new_occupancy > (old_occupancy * 1.25):
                return True
            return False
        elif new_occupancy > 10 or new_occupancy <= 50:
            if new_occupancy < (average_occupancy * 0.9) or new_occupancy > (average_occupancy * 1.1) or \
                new_occupancy < (old_occupancy * 0.9) or new_occupancy > (old_occupancy * 1.1):
                return True
            return False
        elif new_occupancy > 50  or new_occupancy <= 75:
            if new_occupancy < (average_occupancy * 0.95) or new_occupancy > (average_occupancy * 1.05) or \
                new_occupancy < (old_occupancy * 0.95) or new_occupancy > (old_occupancy * 1.05):
                return True
            return False
        elif new_occupancy > 75:
            if new_occupancy < (average_occupancy * 0.975) or new_occupancy > (average_occupancy * 1.025) or \
                new_occupancy < (old_occupancy * 0.975) or new_occupancy > (old_occupancy * 1.025):
                return True
            return False

    def evaluate_movement(self):
        lvaps = RUNTIME.tenants[self.tenant.tenant_id].lvaps
        for lvap in lvaps.values():
            block = lvap.blocks[0]

            if block.addr.to_str() + lvap.addr.to_str() not in self.wifi_data or \
                self.wifi_data[block.addr.to_str() + lvap.addr.to_str()]['rssi'] is None:
                continue

            if self.wifi_data[block.addr.to_str() + lvap.addr.to_str()]['rssi'] < -85 and len(self.stations_aps_matrix[lvap.addr.to_str()]) >= 2:
                self.evaluate_lvap_revert(lvap)
        

    def loop(self):
        """ Periodic job. """

        if self.warm_up_phases > 0 and self.initial_setup:
            self.warm_up_phases -= 1
        elif self.warm_up_phases == 0 and self.initial_setup:
            #Message to the APs to change the channel
            self.initial_setup = False
        elif not self.initial_setup:
            if self.handover_occupancies:
                self.evaluate_handover()

            self.evaluate_movement()

def launch(tenant_id, period=1000):
    """ Initialize the module. """

    return WifiLoadBalancing(tenant_id=tenant_id, every=period)
