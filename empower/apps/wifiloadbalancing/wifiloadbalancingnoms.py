#!/usr/bin/env python3
#
# Copyright (c) 2016 Roberto Riggio
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

"""Ping-pong handover App."""
import random

from empower.core.app import EmpowerApp
from empower.core.app import DEFAULT_PERIOD
from empower.datatypes.etheraddress import EtherAddress
from empower.core.resourcepool import ResourceBlock
from empower.main import RUNTIME
from empower.maps.ucqm import ucqm
from empower.maps.ucqm import UCQMWorker
from empower.bin_counter.bin_counter import BinCounterWorker
from empower.bin_counter.bin_counter import BinCounter
from empower.events.wtpup import wtpup
from empower.events.wtpdown import wtpdown
from empower.events.lvapjoin import lvapjoin
from empower.events.lvapleave import lvapleave
from empower.lvap_stats.lvap_stats import lvap_stats
from empower.lvap_stats.lvap_stats import LVAPStatsWorker
from empower.lvapp import CHANNEL_SWITCH_ANNOUNCEMENT_TO_LVAP
from empower.lvapp import PT_CHANNEL_SWITCH_ANNOUNCEMENT_TO_LVAP
from empower.lvapp import UPDATE_WTP_CHANNEL
from empower.lvapp import PT_UPDATE_WTP_CHANNEL
from empower.core.resourcepool import BANDS


GRAPH_TOP_BOTTOM_MARGIN = 40
GRAPH_LEFT_RIGHT_MARGIN = 40
GRAPH_MAX_WIDTH = 550 - GRAPH_LEFT_RIGHT_MARGIN
GRAPH_MAX_HEIGHT = 750 - GRAPH_TOP_BOTTOM_MARGIN
MIN_DISTANCE = 70
N_XY = 300
RSSI_LIMIT = 10

class WifiLoadBalancing(EmpowerApp):
    """Ping-pong handover App.

    Command Line Parameters:

        tenant_id: tenant id
        lvap: the lvap address (optinal, default 00:18:DE:CC:D3:40)
        wtps: comma separated list (optional, default 00:0D:B9:2F:56:58,
            00:0D:B9:2F:56:5C, 00:0D:B9:2F:56:64)
        every: loop period in ms (optional, default 5000ms)

    Example:

        ./empower-runtime.py apps.pingpong.pingpong \
            --tenant_id=52313ecb-9d00-4b7d-b873-b55d3d9ada26D
    """

    def __init__(self, **kwargs):

        EmpowerApp.__init__(self, **kwargs)
        self.idx = 0

        # Generating inital coordinates for the graph nodes
        self.coord = self.get_coordinates()

        self.wifi_data = {}
        self.bitrate_data_active = {}
        
        self.graphData = {}

        self.total_tx_bytes_per_second = {}
        self.total_rx_bytes_per_second = {}
        self.nb_app_active = {}

        self.stations_channels_matrix = {}
        self.stations_aps_matrix = {}

        self.initial_setup = True
        self.warm_up_phases = 20

        self.conflict_aps = {}
        self.aps_channels_matrix = {}
        # self.channels_bg = [1, 6, 11]
        # self.channels_an = [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 123, 136, 140]
        self.channels_bg = [1, 6, 11]
        #self.channels_an = [56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 140]
        self.channels_an = [149, 153, 157, 161, 165]
        self.aps_clients_rel = {}
        self.aps_occupancy = {}

        # Register an wtp up event
        self.wtpup(callback=self.wtp_up_callback)
        self.wtpdown(callback=self.wtp_down_callback)

        # Register an lvap join event
        self.lvapjoin(callback=self.lvap_join_callback)
        self.lvapleave(callback=self.lvap_leave_callback)

    def get_coordinates(self):

        rangeX = (GRAPH_LEFT_RIGHT_MARGIN, GRAPH_MAX_WIDTH)
        rangeY = (GRAPH_TOP_BOTTOM_MARGIN, GRAPH_MAX_HEIGHT)

        deltas = set()
        for x in range(-MIN_DISTANCE, MIN_DISTANCE + 1):
            for y in range(-MIN_DISTANCE, MIN_DISTANCE + 1):
                if (x * x) + (y * y) >= MIN_DISTANCE * MIN_DISTANCE:
                    deltas.add((x,y))

        randPoints = []
        excluded = set()
        count = 0
        while count < N_XY:
            x = random.randrange(*rangeX)
            y = random.randrange(*rangeY)

            if (x, y) in excluded:
                continue

            randPoints.append((x, y))
            count += 1

            excluded.update((x + dx, y + dy) for (dx, dy) in deltas)

        return randPoints

    def to_dict(self):
        """Return json-serializable representation of the object."""

        out = super().to_dict()
        out['wifi_data'] = self.wifi_data

        stations_aps_matrix = {str(k): v for k, v in self.stations_aps_matrix.items()}
        total_rx_bytes_per_second = {str(k): v for k, v in self.total_rx_bytes_per_second.items()}
        total_tx_bytes_per_second = {str(k): v for k, v in self.total_tx_bytes_per_second.items()}
        stations_channels_matrix = {str(k): v for k, v in self.stations_channels_matrix.items()}
        conflict_aps = {str(k): v for k, v in self.conflict_aps.items()}

        out['total_rx_bytes_per_second'] = total_rx_bytes_per_second
        out['total_tx_bytes_per_second'] = total_tx_bytes_per_second
        out['aps_clients_rel'] = self.aps_clients_rel
        out['graphData'] = self.graphData
        out['conflict_aps'] = self.conflict_aps
        out['stations_aps_matrix'] = self.stations_aps_matrix
        out['bitrate_data_active'] = self.bitrate_data_active

        return out


    def wtp_up_callback(self, wtp):
        """Called when a new WTP connects to the controller."""

        lvaps = RUNTIME.tenants[self.tenant.tenant_id].lvaps

        for block in wtp.supports:
            # channels = self.channels_bg + self.channels_an
            # new_channel = random.choice(channels)
            #     # If it holds any lvap... 
            # self.update_block(block, new_channel)

            # for lvap in lvaps.values():
            #     if lvap.default_block.addr != block.addr:
            #         continue
            #     lvap.scheduled_on = block
            #     self.update_counters(lvap)

            self.ucqm(block=block,
                        tenant_id=self.tenant.tenant_id,
                        every=self.every,
                        callback=self.ucqm_callback)

            if block.addr.to_str() not in self.conflict_aps:
                self.conflict_aps[block.addr.to_str()] = []
            if block.addr.to_str() not in self.aps_clients_rel:
                self.aps_clients_rel[block.addr.to_str()] = []

            if block.addr.to_str() not in self.aps_channels_matrix:
                self.aps_channels_matrix[block.addr.to_str()] = block.channel

            if block.addr.to_str() not in self.bitrate_data_active:
                self.bitrate_data_active[block.addr.to_str()] = {}

            if block.addr.to_str() not in self.total_tx_bytes_per_second:
                self.total_tx_bytes_per_second[block.addr.to_str()] = 0
            if block.addr.to_str() not in self.total_rx_bytes_per_second:
                self.total_rx_bytes_per_second[block.addr.to_str()] = 0

            if block.addr.to_str() not in self.nb_app_active:
                self.nb_app_active[block.addr.to_str()] = 0

            if block.addr.to_str() not in self.aps_channels_matrix:
                self.aps_channels_matrix[block.addr.to_str()] = block.channel
    

    def wtp_down_callback(self, wtp):
        """Called when a wtp connectdiss from the controller."""

        lvaps = RUNTIME.tenants[self.tenant.tenant_id].lvaps

        for block in wtp.supports:
            self.delete_ucqm_worker(block)

            for lvap in lvaps.values():
                if lvap.default_block != block:
                    continue

                self.delete_bincounter_worker(lvap)
                self.delete_lvap_stats_worker(lvap)


            if block.addr.to_str() in self.conflict_aps:
                del self.conflict_aps[block.addr.to_str()]

            for key, values in self.conflict_aps.items():
                if block.addr.to_str() in values:
                    values.remove(block.addr.to_str())
                    break

            if block.addr.to_str() in self.aps_channels_matrix:
                del self.aps_channels_matrix[block.addr.to_str()]

            if block.addr.to_str() in self.bitrate_data_active:
                del self.bitrate_data_active[block.addr.to_str()] 

            if block.addr.to_str() in self.total_tx_bytes_per_second:
                del self.total_tx_bytes_per_second[block.addr.to_str()]
            if block.addr.to_str() in self.total_rx_bytes_per_second:
                del self.total_rx_bytes_per_second[block.addr.to_str()]

            if block.addr.to_str() in self.nb_app_active:
                del self.nb_app_active[block.addr.to_str()]

            if block.addr.to_str() in self.aps_channels_matrix:
                del self.aps_channels_matrix[block.addr.to_str()]


    def lvap_join_callback(self, lvap):
        """Called when an joins the network."""

        self.update_counters(lvap)
        self.aps_clients_rel[lvap.default_block.addr.to_str()].append(lvap.addr.to_str())

    def lvap_leave_callback(self, lvap):
        """Called when an LVAP disassociates from a tennant."""

        self.delete_bincounter_worker(lvap)
        self.delete_lvap_stats_worker(lvap)

        if lvap.addr.to_str() in self.aps_clients_rel[lvap.default_block.addr.to_str()]:
            self.aps_clients_rel[lvap.default_block.addr.to_str()].remove(lvap.addr.to_str())
        if lvap.addr.to_str() in self.bitrate_data_active[lvap.default_block.addr.to_str()]:
            del self.bitrate_data_active[lvap.default_block.addr.to_str()][lvap.addr.to_str()]

    def lvap_stats_callback(self, counter):
        """ New stats available. """

        rates = (counter.to_dict())["rates"]
        if not rates or counter.lvap not in RUNTIME.lvaps:
            return

        lvap = RUNTIME.lvaps[counter.lvap]
        highest_rate = int(float(max(rates, key=lambda v: int(float(rates[v]['prob'])))))

        key = lvap.default_block.addr.to_str() + lvap.addr.to_str()

        if key in self.wifi_data:
            if self.wifi_data[key]['rate'] is None:
                self.wifi_data[key]['rate'] = highest_rate
            elif highest_rate < self.wifi_data[key]['rate']:
                self.wifi_data[key]['rate_attempts'] += 1
        else:
            self.wifi_data[key] = \
                        {
                            'rssi': None,
                            'wtp': lvap.default_block.addr.to_str(),
                            'sta': lvap.addr.to_str(),
                            'channel': lvap.default_block.channel,
                            'active': 1,
                            'tx_bytes_per_second': None,
                            'rx_bytes_per_second': None,
                            'old_tx_bytes_per_second': None,
                            'old_rx_bytes_per_second': None,
                            'reesched_attempts': 0,
                            'revert_attempts': 0,
                            'rate': highest_rate,
                            'rate_attempts': 0
                        }

        if self.wifi_data[key]['rate_attempts'] < 5:
            return

        self.wifi_data[key]['rate'] = highest_rate
        self.wifi_data[key]['rate_attempts'] = 0
        self.evalute_lvap_revert(lvap)

    def counters_callback(self, stats):
        """ New stats available. """

        self.log.info("New counters received from %s" % stats.lvap)

        lvap = RUNTIME.lvaps[stats.lvap]
        block = lvap.default_block

        if (not stats.tx_bytes_per_second and not stats.rx_bytes_per_second) and \
            (block.addr.to_str() + stats.lvap.to_str() not in self.wifi_data):
            print("-----It's null")
            return

        if not stats.tx_bytes_per_second:
            stats.tx_bytes_per_second = []
            stats.tx_bytes_per_second.append(0)
        if not stats.rx_bytes_per_second:
            stats.rx_bytes_per_second = []
            stats.rx_bytes_per_second.append(0)

        self.counters_to_file(lvap, block, stats)

        key = block.addr.to_str() + stats.lvap.to_str()

        if key in self.wifi_data:
            self.wifi_data[key]['tx_bytes_per_second'] = stats.tx_bytes_per_second[0]
            self.wifi_data[key]['rx_bytes_per_second'] = stats.rx_bytes_per_second[0]

            if not self.wifi_data[key]['old_tx_bytes_per_second']:
                self.wifi_data[key]['old_tx_bytes_per_second'] = stats.tx_bytes_per_second[0]
            if not self.wifi_data[key]['old_rx_bytes_per_second']:
                self.wifi_data[key]['old_rx_bytes_per_second'] = stats.rx_bytes_per_second[0]
        else:
            self.wifi_data[block.addr.to_str() + stats.lvap.to_str()] = \
                        {
                            'rssi': None,
                            'wtp': block.addr.to_str(),
                            'sta': stats.lvap.to_str(),
                            'channel': lvap.default_block.channel,
                            'active': 1,
                            'tx_bytes_per_second': stats.tx_bytes_per_second[0],
                            'rx_bytes_per_second': stats.rx_bytes_per_second[0],
                            'old_tx_bytes_per_second': stats.tx_bytes_per_second[0],
                            'old_rx_bytes_per_second': stats.rx_bytes_per_second[0],
                            'reesched_attempts': 0,
                            'revert_attempts': 0,
                            'rate': 0,
                            'rate_attempts': 0
                        }
                            

        possible_revert_lvap = False
        possible_resched_lvap = False
        # Minimum voice bitrates:
        # https://books.google.it/books?id=ExeKR1iI8RgC&pg=PA88&lpg=PA88&dq=bandwidth+consumption+per+application+voice+video+background&source=bl&ots=1zUvCgqAhZ&sig=5kkM447M4t9ezbVDde3-D3oh2ww&hl=it&sa=X&ved=0ahUKEwiRuvOJv6vUAhWPDBoKHYd5AysQ6AEIWDAG#v=onepage&q=bandwidth%20consumption%20per%20application%20voice%20video%20background&f=false
        # https://www.voip-info.org/wiki/view/Bandwidth+consumption
        # G729A codec minimum bitrate 17K 17804
        if lvap.addr.to_str() in self.bitrate_data_active[block.addr.to_str()]:
            if stats.tx_bytes_per_second[0] >= 500:
                # This means the app was already active or it was not there
                self.bitrate_data_active[block.addr.to_str()][lvap.addr.to_str()]['tx_bytes_per_second'] = stats.tx_bytes_per_second[0]
            else:
                # if self.bitrate_data_active[block.addr.to_str()][lvap.addr.to_str()]['tx_bytes_per_second'] >= 500:
                self.bitrate_data_active[block.addr.to_str()][lvap.addr.to_str()]['tx_bytes_per_second'] = 0

            if stats.rx_bytes_per_second[0] >= 500:
                # This means the app was already active or it was not there
                self.bitrate_data_active[block.addr.to_str()][lvap.addr.to_str()]['rx_bytes_per_second'] = stats.rx_bytes_per_second[0]
            else:
                # if self.bitrate_data_active[block.addr.to_str()][lvap.addr.to_str()]['rx_bytes_per_second'] >= 500:
                self.bitrate_data_active[block.addr.to_str()][lvap.addr.to_str()]['rx_bytes_per_second'] = 0

            if (self.bitrate_data_active[block.addr.to_str()][lvap.addr.to_str()]['tx_bytes_per_second'] >= 500 and self.wifi_data[key]['tx_bytes_per_second'] > self.wifi_data[key]['old_tx_bytes_per_second']) or \
                (self.bitrate_data_active[block.addr.to_str()][lvap.addr.to_str()]['rx_bytes_per_second'] >= 500 and self.wifi_data[key]['rx_bytes_per_second'] > self.wifi_data[key]['old_rx_bytes_per_second']):
                self.wifi_data[key]['reesched_attempts'] += 1

            if (self.bitrate_data_active[block.addr.to_str()][lvap.addr.to_str()]['tx_bytes_per_second'] < 500 and self.wifi_data[key]['tx_bytes_per_second'] < self.wifi_data[key]['old_tx_bytes_per_second']) and \
                (self.bitrate_data_active[block.addr.to_str()][lvap.addr.to_str()]['rx_bytes_per_second'] < 500 and self.wifi_data[key]['rx_bytes_per_second'] < self.wifi_data[key]['old_rx_bytes_per_second']):
                self.wifi_data[key]['reesched_attempts'] = 0
                self.wifi_data[key]['revert_attempts'] += 1
                
        else:
            if stats.tx_bytes_per_second[0] >= 500:
                self.bitrate_data_active[block.addr.to_str()][lvap.addr.to_str()] = \
                                            {
                                                'tx_bytes_per_second': stats.tx_bytes_per_second[0],
                                                'rx_bytes_per_second': 0
                                            }
                self.wifi_data[key]['reesched_attempts'] += 1
                                    
            if stats.rx_bytes_per_second[0] >= 500:
                self.bitrate_data_active[block.addr.to_str()][lvap.addr.to_str()] = \
                                            {
                                                'tx_bytes_per_second': 0,
                                                'rx_bytes_per_second': stats.rx_bytes_per_second[0]
                                            }
                self.wifi_data[key]['reesched_attempts'] += 1


            if (stats.rx_bytes_per_second[0] < 500) and (stats.tx_bytes_per_second[0] < 500):
                self.wifi_data[key]['revert_attempts'] += 1


        print("------self.bitrate_data_active[block]", self.bitrate_data_active[block.addr.to_str()])

        if self.wifi_data[key]['revert_attempts'] >= 5:
            if lvap.addr.to_str() in self.bitrate_data_active[block.addr.to_str()]:
                del self.bitrate_data_active[block.addr.to_str()][lvap.addr.to_str()]
            self.wifi_data[key]['revert_attempts'] = 0
            possible_revert_lvap = True
        elif self.wifi_data[key]['reesched_attempts'] >= 5 and self.nb_app_active[block.addr.to_str()] > 1:
            self.wifi_data[key]['reesched_attempts'] = 0
            possible_resched_lvap = True

        self.update_transmission_traffic(block)

        if not possible_revert_lvap and not possible_resched_lvap:
            print("NO SCHEDULING")
            return

        self.wifi_data[key]['old_tx_bytes_per_second'] = self.wifi_data[key]['tx_bytes_per_second']
        self.wifi_data[key]['old_rx_bytes_per_second'] = self.wifi_data[key]['rx_bytes_per_second']
        
        if possible_revert_lvap:
            self.evalute_lvap_revert(lvap)
        elif possible_resched_lvap:
            self.evalute_lvap_scheduling(lvap)


    def counters_to_file(self, lvap, block, summary):
        """ New stats available. """

        # per block log
        filename = "wifiloadbalancing_%s_%u_%s.csv" % (block.addr.to_str(),
                                            block.channel,
                                            BANDS[block.band])


        line = "%f,%d,%d\n" % \
            (int(round(summary.last * 1000)), summary.rx_bytes_per_second[0], summary.tx_bytes_per_second[0])

        with open(filename, 'a') as file_d:
            file_d.write(line)

        # per link log

        link = "%s_%s_%u_%s" % (lvap.addr.to_str(), block.addr.to_str(),
                                block.channel,
                                BANDS[block.band])

        filename = "wifiloadbalancing_link_%s.csv" % link

        line = "%f,%d,%d\n" % \
            (int(round(summary.last * 1000)), summary.rx_bytes_per_second[0], summary.tx_bytes_per_second[0])

        with open(filename, 'a') as file_d:
            file_d.write(line)


    def update_transmission_traffic(self, block):

        self.nb_app_active[block.addr.to_str()] = len(self.bitrate_data_active[block.addr.to_str()])
        temp_total_tx_bytes_per_second = 0
        temp_total_rx_bytes_per_second = 0

        for sta in self.bitrate_data_active[block.addr.to_str()].values():
            temp_total_tx_bytes_per_second += sta['tx_bytes_per_second']
            temp_total_rx_bytes_per_second += sta['rx_bytes_per_second']


        self.total_tx_bytes_per_second[block.addr.to_str()] = temp_total_tx_bytes_per_second
        self.total_rx_bytes_per_second[block.addr.to_str()] = temp_total_rx_bytes_per_second


        ########## Estimation of the channel occupancy of the candidate APs ###########
        
        if block.addr.to_str() not in self.aps_clients_rel:
            self.aps_occupancy[block.addr.to_str()] = 0
            return 

        occupation = 0
        for sta in self.aps_clients_rel[block.addr.to_str()]:
            if block.addr.to_str() + sta not in self.wifi_data or \
                self.wifi_data[block.addr.to_str() + sta]['tx_bytes_per_second'] is None or \
                self.wifi_data[block.addr.to_str() + sta]['rx_bytes_per_second'] is None:
                self.aps_occupancy[block.addr.to_str()] = 0
                return

            if self.wifi_data[block.addr.to_str() + sta]['rate'] == 0:
                continue
            occupation += ((self.wifi_data[block.addr.to_str() + sta]['tx_bytes_per_second'] \
                            + self.wifi_data[block.addr.to_str() + sta]['rx_bytes_per_second']) * 8 \
                            / self.wifi_data[block.addr.to_str() + sta]['rate']) / 1000000

        self.aps_occupancy[block.addr.to_str()] = occupation


    def evalute_lvap_revert(self, lvap):

        block = lvap.default_block
        new_block = None

        if block.addr.to_str() + lvap.addr.to_str() not in self.wifi_data or \
           self.wifi_data[block.addr.to_str() + lvap.addr.to_str()]['rssi'] is None:
           return 

        current_rssi = self.wifi_data[block.addr.to_str() + lvap.addr.to_str()]['rssi']
        best_rssi = -120

        print("------self.total_tx_bytes_per_second[block.addr.to_str()] ", self.total_tx_bytes_per_second[block.addr.to_str()] )
        print("------self.total_rx_bytes_per_second[block.addr.to_str()]", self.total_rx_bytes_per_second[block.addr.to_str()])
        print("------self.nb_app_active[block]", self.nb_app_active[block.addr.to_str()])

        print("++++++++COME BACK++++++++")
        print("------current_rssi", current_rssi)

        if lvap.addr.to_str() not in self.stations_aps_matrix:
            return

        for wtp in self.stations_aps_matrix[lvap.addr.to_str()]:
            if wtp == block.addr.to_str():
                continue
            print("rssi of %s: %d" %(wtp, self.wifi_data[wtp + lvap.addr.to_str()]['rssi'] ))
            if self.wifi_data[wtp + lvap.addr.to_str()]['rssi'] <= (current_rssi + RSSI_LIMIT) or \
                self.wifi_data[wtp + lvap.addr.to_str()]['rssi'] < best_rssi:
                continue

            best_rssi = self.wifi_data[wtp + lvap.addr.to_str()]['rssi']
            new_block = self.get_block_for_ap_addr(wtp)

        if not new_block:
            return

        self.transfer_block_data(block, new_block, lvap)
        self.update_transmission_traffic(block)
        self.update_transmission_traffic(new_block)
        
        lvap.scheduled_on = new_block


    def evalute_lvap_scheduling(self, lvap):

        block = lvap.default_block
        new_block = None

        print("------self.total_tx_bytes_per_second[block.addr.to_str()] ", self.total_tx_bytes_per_second[block.addr.to_str()] )
        print("------self.total_rx_bytes_per_second[block.addr.to_str()]", self.total_rx_bytes_per_second[block.addr.to_str()])
        print("------self.nb_app_active[block]", self.nb_app_active[block.addr.to_str()])

        clients_candidates = {}
        # It is not necessary to perform a change if the traffic of the ap is lower than the average or if it is holding a single lvap
        if block.addr.to_str() not in self.aps_occupancy:
            print("NOTHING HERE")
            return

        #average_traffic = self.average_traffic_surrounding_aps(lvap)
        average_occupancy = self.average_occupancy_surrounding_aps(lvap)
        if self.aps_occupancy[block.addr.to_str()] <= average_traffic or self.nb_app_active[block.addr.to_str()] < 2:
            print("NOT ENOUGH TRAFFIC")
            print("average traffic", average_traffic)
            print("self.total_tx_bytes_per_second[block.addr.to_str()] + self.total_rx_bytes_per_second[block.addr.to_str()]", (self.total_tx_bytes_per_second[block.addr.to_str()] + self.total_rx_bytes_per_second[block.addr.to_str()]))
            return

        ########## Look for the lvaps from this wtp that can be reescheduled ###########
        clients_candidates[sta] = []

        for sta in self.aps_clients_rel[block.addr.to_str()]:
            if sta not in self.stations_aps_matrix or len(self.stations_aps_matrix[sta]) < 2:
                continue

            current_sta_rssi = self.wifi_data[block.addr.to_str() + sta]['rssi']
            
            for wtp in self.stations_aps_matrix[sta]:
                #TODO. ADD THRES. WHEN THE UNITS OF THE OCCUPANCY ARE NOWN
                if wtp == block.addr.to_str():
                    continue

                if self.aps_occupancy[wtp] > self.aps_occupancy[block.addr.to_str()] \
                    or self.wifi_data[wtp + sta]['rssi'] < 85:
                    continue

                conflict_occupancy = 0
                wtp_channel = self.aps_channels_matrix[wtp]
                if wtp in self.conflict_aps:
                    for neigh in self.conflict_aps[wtp].values():
                        if self.aps_channels_matrix[neigh] != wtp_channel:
                            continue 
                        conflict_occupancy += self.aps_occupancy[neigh]

                wtp_info = \
                    {
                        'wtp': wtp,
                        'metric' : abs(self.wifi_data[wtp + sta]['rssi']) * self.aps_occupancy[wtp],
                        'conf_occupancy': conflict_occupancy,
                        'conf_metric': abs(self.wifi_data[wtp + sta]['rssi']) * conflict_occupancy
                    }
                clients_candidates[sta].append(wtp_info)
            
            if len(clients_candidates[sta]) == 0:
                del clients_candidates[sta]

        if len(clients_candidates) == 0:
            print("Not possible reescheduling. The network is balanced")
            return

        ########## Evaluate list of candidates lvaps-wtsp ###########
        highest_metric = sys.maxsize
        best_wtp = None
        best_lvap = None
        candidate_channel = None
        for sta, wtps in clients_candidates.items():
            for ap in wtps:
                if ap['metric'] < highest_metric and ap['conf_metric'] < highest_metric:
                    highest_metric = ap[metric]
                    best_wtp = ap
                    best_lvap = sta
                elif ap['metric'] < highest_metric and ap['conf_metric'] >= highest_metric:
                    candidate_block = self.get_block_for_ap_addr(ap['wtp'])
                    candidate_channel = self.find_new_channel(candidate_block)
                    if not candidate_channel:
                        continue
                    highest_metric = ap[metric]
                    best_wtp = ap
                    best_lvap = sta


        print("PERFORMING HANDOVER")
        new_block = self.get_block_for_ap_addr(best_wtp)
        new_lvap = RUNTIME.lvaps[best_lvap]
    
        if candidate_channel:
            self.switch_channel_in_block(new_block, candidate_channel)
            new_block.channel = candidate_channel

        self.transfer_block_data(block, new_block, new_lvap)
        self.update_transmission_traffic(block)
        self.update_transmission_traffic(new_block)

        print("++++++++ new block", new_block.addr.to_str())
        print("++++++++ old block", block.addr.to_str())
        print("++++++++++++ self.nb_app_active[block.addr.to_str()]", self.nb_app_active[block.addr.to_str()])
        print("++++++++++++ self.nb_app_active[new_block.addr.to_str()]", self.nb_app_active[new_block.addr.to_str()])

        new_lvap.scheduled_on = new_block


    def find_new_channel(sefl, new_block):
        # Check if there are APs in the same channel
        channel_switch = False
        unavailable_channels = []
        self.conflict_graph()
        for ap in self.conflict_aps[new_block.addr.to_str()]:
                if self.aps_channels_matrix[new_block.addr.to_str()] != self.aps_channels_matrix[ap] and \
                    self.nb_app_active[ap] >= 1:
                    unavailable_channels.append(self.aps_channels_matrix[ap])
                else:
                    channel_switch = True

        print("---- current channel ", self.aps_channels_matrix[new_block.addr.to_str()])
        print("---- channel needed", channel_switch)
        
        # Calculate if it is needed a new channel change. 
        if not channel_switch:
            return None

        new_channel = None
        first_band_list = None
        second_band_list = None
        # First it attempts to mantain the same frequency band
        if new_block.channel in self.channels_bg:
            first_band_list = self.channels_bg
            second_band_list = self.channels_an
        else:
            first_band_list = self.channels_an
            second_band_list = self.channels_bg

        # First frequency band
        for entry in first_band_list:
            if new_block.channel == entry:
                continue
            if entry in unavailable_channels:
                continue
            new_channel = entry
            break

        print ("---- 1 try. new channel", new_channel)

        # If any available channel in the same frequency band, it checks the second one
        if not new_channel:
            for entry in second_band_list:
                if self.aps_channels_matrix[new_block.addr.to_str()] == entry:
                    continue
                if entry in unavailable_channels:
                    continue
                new_channel = entry
                break
            print ("---- 2 try. new channel", new_channel)

        # If all the channels are busy, it picks the one holding the lowest number of APs
        if not new_channel:
            new_channel = min(self.stations_channels_matrix[lvap.addr.to_str()].keys(), key=(lambda k: stations_channels_matrix[lvap.addr.to_str()][k]))
            print ("---- worst try. new channel", new_channel)

        return new_channel

    def delete_ucqm_worker(self, block):
        worker = RUNTIME.components[UCQMWorker.__module__]

        for module_id in list(worker.modules.keys()):
            ucqm_mod = worker.modules[module_id]
            if block == ucqm_mod.block:
                worker.remove_module(module_id)

    def delete_bincounter_worker(self, lvap):
        worker = RUNTIME.components[BinCounterWorker.__module__]

        for module_id in list(worker.modules.keys()):
            bincounter_mod = worker.modules[module_id]
            if lvap == bincounter_mod.lvap:
                worker.remove_module(module_id)

    def delete_lvap_stats_worker(self, lvap):
        worker = RUNTIME.components[LVAPStatsWorker.__module__]

        for module_id in list(worker.modules.keys()):
            lvap_stats_mod = worker.modules[module_id]
            if lvap == lvap_stats_mod.lvap:
                worker.remove_module(module_id)

    def update_block(self, block, channel):

        self.delete_ucqm_worker(block)
            
        block.channel = channel

        ucqm_mod = self.ucqm(block=block,
                        tenant_id=self.tenant.tenant_id,
                        every=self.every,
                        callback=self.ucqm_callback)

        if block.addr.to_str() in self.aps_clients_rel:
            for lvap in self.aps_clients_rel[block.addr.to_str()]:
                self.wifi_data[block.addr.to_str() + lvap]['channel'] = channel

        self.aps_channels_matrix[block.addr.to_str()] = channel


    def update_counters(self, lvap):

        self.delete_bincounter_worker(lvap)
        self.bin_counter(lvap=lvap.addr,
                 every=500,
                 callback=self.counters_callback)

        self.delete_lvap_stats_worker(lvap)
        self.lvap_stats(lvap=lvap.addr, 
                    every=500, 
                    callback=self.lvap_stats_callback)


    def transfer_block_data(self, src_block, dst_block, lvap):

        if lvap.addr.to_str() in self.aps_clients_rel[src_block.addr.to_str()]:
            self.aps_clients_rel[src_block.addr.to_str()].remove(lvap.addr.to_str())
        if lvap.addr.to_str() not in self.aps_clients_rel[dst_block.addr.to_str()]:
            self.aps_clients_rel[dst_block.addr.to_str()].append(lvap.addr.to_str())

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
        self.wifi_data[src_block.addr.to_str() + lvap.addr.to_str()]['tx_bytes_per_second'] = 0
        self.wifi_data[src_block.addr.to_str() + lvap.addr.to_str()]['rx_bytes_per_second'] = 0


    def conflict_graph(self):

        for wtp_list in self.stations_aps_matrix.values():
            for wtp in wtp_list:
                for conflict_wtp in wtp_list:
                    if conflict_wtp != wtp and (conflict_wtp not in self.conflict_aps[wtp]):
                        self.conflict_aps[wtp].append(conflict_wtp)

        for wtp_list in self.stations_aps_matrix.values():
            for wtp in wtp_list:
                for conflict_wtp in wtp_list:
                    if conflict_wtp != wtp and (conflict_wtp not in self.conflict_aps[wtp]):
                        self.conflict_aps[wtp].append(conflict_wtp)


    def ucqm_callback(self, poller):
        """Called when a UCQM response is received from a WTP."""

        lvaps = RUNTIME.tenants[self.tenant.tenant_id].lvaps
        self.ucqm_resp = poller

        for addr in poller.maps.values():

            # This means that this lvap is attached to a WTP in the network.
            if addr['addr'] in lvaps and lvaps[addr['addr']].wtp:
                active_flag = 1

                if (lvaps[addr['addr']].wtp.addr != poller.block.addr):
                    active_flag = 0
                elif ((lvaps[addr['addr']].wtp.addr == poller.block.addr  \
                    and (lvaps[addr['addr']].association_state == False))):
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
                                        'tx_bytes_per_second': None,
                                        'rx_bytes_per_second': None,
                                        'old_tx_bytes_per_second': None,
                                        'old_rx_bytes_per_second': None,
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


                self.stations_channels_matrix[addr['addr'].to_str()] = {}

                if poller.block.channel not in self.stations_channels_matrix[addr['addr'].to_str()]:
                    self.stations_channels_matrix[addr['addr'].to_str()][poller.block.channel] = 1
                else:
                    number = self.stations_channels_matrix[addr['addr'].to_str()][poller.block.channel]
                    self.stations_channels_matrix[addr['addr'].to_str()][poller.block.channel] = number + 1


            elif poller.block.addr.to_str() + addr['addr'].to_str() in self.wifi_data:
                del self.wifi_data[poller.block.addr.to_str() + addr['addr'].to_str()]

    def set_random_channels(self):

        wtps = RUNTIME.tenants[self.tenant.tenant_id].wtps
        channels = self.channels_bg + self.channels_an
        lvaps = RUNTIME.tenants[self.tenant.tenant_id].lvaps

        for wtp in wtps.values():
            for block in wtp.supports:
                new_channel = random.choice(channels)
                # If it holds any lvap... 
                self.update_block(block, new_channel)

                for lvap in lvaps.values():
                    if lvap.default_block.addr != block.addr:
                        continue
                    lvap.scheduled_on = block
                    self.update_counters(lvap)


                if block.addr.to_str() not in self.aps_clients_rel:
                    self.aps_clients_rel[block.addr.to_str()] = []

                    for lvap in lvaps.values():
                        if lvap.default_block.addr != block.addr:
                            continue
                        self.aps_clients_rel[block.addr.to_str()].append(lvap.addr.to_str())

                for lvap in self.aps_clients_rel[block.addr.to_str()]:
                    self.wifi_data[block.addr.to_str() + lvap]['channel'] = new_channel

    def switch_channel_in_block(self, req_block, channel):

        wtps = RUNTIME.tenants[self.tenant.tenant_id].wtps

        for wtp in wtps.values():
            for block in wtp.supports:
                if block != req_block:
                    continue

                initial_channel = block.channel
                block.channel = channel

                for lvap in lvaps.values():
                    if lvap.default_block != block:
                        continue
                    
                    for b in lvap.supported:
                        if b.addr != block.addr:
                            continue
                        b.channel = channel
                        break
                    lvap.scheduled_on = block
                    self.update_counters(lvap)
                
                block.radio.connection.send_channel_switch_request(channel, block.hwaddr, initial_channel, block.band)
                self.update_block(block, channel)

                for lvap in self.aps_clients_rel[block.addr.to_str()]:
                    self.wifi_data[block.addr.to_str() + lvap]['channel'] = channel

                return

    def average_occupancy_surrounding_aps(self, lvap):
        average_occupancy = 0

        for key, wtp in enumerate(self.stations_aps_matrix[lvap.addr.to_str()]):
            if wtp not in self.aps_occupancy:
                continue
            average_occupancy += self.aps_occupancy[wtp]
            print("TRAFFIC IN AVERAGE", self.aps_occupancy[wtp])

        print(len(self.stations_aps_matrix[lvap.addr.to_str()]))
        return (average_occupancy / len(self.stations_aps_matrix[lvap.addr.to_str()]))


    def get_block_for_ap_addr(self, addr):
        wtps = RUNTIME.tenants[self.tenant.tenant_id].wtps
        for wtp in wtps.values():
            for block in wtp.supports:
                if block.addr.to_str() != addr:
                    continue
                return block

        return None


    def loop(self):
        """ Periodic job. """

        node_id = 0
        # Contains all links between cells and UEs
        graph_links = []
        # Contains all nodes in the graph
        graph_nodes = {}

        tenant = RUNTIME.tenants[self.tenant.tenant_id]

        # Populate existing WTPs and trigger UCQM for existing WTPs
        for wtp in self.tenant.wtps.values():
            if not wtp.connection:
                continue

            # Append the WTP's info
            graph_nodes['wtp' + wtp.addr.to_str()] =  \
                                            {
                                                'id': node_id,
                                                'node_id': wtp.addr.to_str(),
                                                'entity': 'wtp',
                                                'tooltip': 'MAC',
                                                'x': self.coord[node_id][0],
                                                'y': self.coord[node_id][1]
                                            }
            node_id += 1

        lvaps = RUNTIME.tenants[self.tenant.tenant_id].lvaps

        for sta in lvaps.values():
            # Append the LVAP's info
            graph_nodes['sta' + sta.addr.to_str()] =  \
                                        {
                                            'id': node_id,
                                            'node_id': sta.addr.to_str(),
                                            'entity': 'sta',
                                            'tooltip': 'MAC',
                                            'x': self.coord[node_id][0],
                                            'y': self.coord[node_id][1]
                                        }

            for k, v in self.wifi_data.items():
                # Check for links pertaining to each WIFI station
                if k.endswith(sta.addr.to_str()):

                    color = 'black'
                    width = 4

                    if v['active'] == 1:
                        width = 6
                        color = 'lightgreen'

                    # Add each link for a measured WTP
                    graph_links.append({
                                        'src': graph_nodes['wtp' + v['wtp']]['id'],
                                        'dst': node_id,
                                        'rssi': v['rssi'],
                                        'entity': 'wifi',
                                        'color': color,
                                        'width': width,
                                        'channel': v['channel'],
                                        'tx_bps': v['tx_bytes_per_second'],
                                        'rx_bps': v['rx_bytes_per_second']
                                       })

            node_id += 1

        self.graphData = {
                            'nodes': graph_nodes.values(),
                            'links': graph_links
                          }

        if self.warm_up_phases > 0 and self.initial_setup:
            self.warm_up_phases -= 1
        elif self.warm_up_phases == 0 and self.initial_setup:
            #Message to the APs to change the channel
            self.initial_setup = False
            #self.revert_channels()
            #self.set_random_channels()
        elif not self.initial_setup and self.warm_up_phases <= 0 and self.warm_up_phases > -80:
            self.warm_up_phases -= 1
        elif not self.initial_setup and self.warm_up_phases == -80:
            self.set_random_channels()
            self.warm_up_phases -= 1


def launch(tenant_id, period=500):
    """ Initialize the module. """

    return WifiLoadBalancing(tenant_id=tenant_id, every=period)