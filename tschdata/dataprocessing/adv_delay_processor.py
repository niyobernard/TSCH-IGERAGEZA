__author__ = 'Mikhail Vilgelm'

import os, re
from os.path import isfile, join
from seaborn.apionly import heatmap
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import gridspec

from dataprocessing.basic_processor import set_box_plot
from dataprocessing.log_processor import LogProcessor
from dataprocessing.toolbox import set_figure_parameters, Schedule


set_figure_parameters()
pd.options.mode.chained_assignment = None
gl_num_active_slots = 13
gl_num_off_slots = 2
gl_num_serial_slots = 2
gl_mote_range = range(1, 14)
gl_dump_path = "../../data/raw"
gl_image_path = '../../SGMeasurements/pics/'
gl_save = False

gl_default_schedule = Schedule(num_slots=gl_num_active_slots, num_off=gl_num_off_slots, num_serial=gl_num_serial_slots)


class AdvDelayProcessor(LogProcessor):

    def __init__(self, **kwargs):
        if 'schedule' in kwargs.keys():
            self.schedule = kwargs.pop('schedule')
        else:
            self.schedule = gl_default_schedule
        super().__init__(**kwargs)

    def get_all_paths_w_delay(self):
        '''
        :return: a list of (path, delay) to delay array values
        '''
        seen_paths = set()

        # paths = pd.DataFrame()
        paths_real = []
        paths_min = []

        for pkt in self.packets:
            if pkt.delay >= 0:
                path = pkt.get_path(full=False)
                if not (str(path) in seen_paths):
                    paths_real.append((path, [pkt.delay]))
                    paths_min.append((path, [self.schedule.get_min_packet_delay(pkt)]))
                    seen_paths.add(str(path))
                else:
                    for idx, t in enumerate(paths_min):
                        if t[0] == path:
                            real_delay = pkt.delay
                            min_delay = self.schedule.get_min_packet_delay(pkt)
                            # debug
                            min_path_delay = self.schedule.get_min_path_delay(t[0])
                            # assert (real_delay >= min_delay)
                            # assert (min_delay >= min_path_delay)

                            paths_min[idx][1].append(min_delay)
                            paths_real[idx][1].append(real_delay)
                            break
            else:
                print('negative delay...')
                print(pkt)

        return paths_real, paths_min

    def get_all_paths_w_num_pkts(self):
        '''
        :return: a hashmap of path to delay array values
        '''
        seen_paths = set()
        paths = []

        for pkt in self.packets:
            path = pkt.get_path(full=False)
            if not (str(path) in seen_paths):
                paths.append([path, 1])
                seen_paths.add(str(path))
            else:
                for idx, t in enumerate(paths):
                    if t[0] == path:
                        paths[idx][1] += 1
                        break

        return paths

    def plot_links_heatmap(self):
        '''

        :return: a hashmap of path to delay array values
        '''
        links = [[0 for i in gl_mote_range] for m in gl_mote_range]

        for pkt in self.packets:
            for idx, hop in enumerate(pkt.hop_info):
                src = hop['addr']
                if idx == (len(pkt.hop_info)-1):
                    dst = 1
                else:
                    dst = pkt.hop_info[idx+1]['addr']
                links[src-1][dst-1] += 1

        plt.figure()
        heatmap(data=links, xticklabels=[i for i in gl_mote_range], yticklabels=[i for i in gl_mote_range])

        if gl_save:
            plt.savefig(gl_image_path+re.findall(r"(.+?)\.log", self.filename.split('/')[-1])[0]+'_link_load.png',
                        format='png', bbox='tight')

    def plot_path_delay(self):

        paths_real, paths_min = self.get_all_paths_w_delay()

        zipped_and_sorted = [(x, y) for (x, y) in sorted(zip(paths_min, paths_real),
                             key=lambda p: self.schedule.get_min_path_delay(p[0][0]))]

        paths_min = [z[0] for z in zipped_and_sorted]
        paths_real = [z[1] for z in zipped_and_sorted]

        # debug
        for idx, p in enumerate(paths_real):
            print(str(p[0]) + ', sample size: %d' % len(p[1]))

        # sort out barely used paths
        paths_real = [p for p in paths_real if len(p[1]) >= 100]
        paths_min = [p for p in paths_min if len(p[1]) >= 100]

        return paths_real, paths_min

    def print_delay(self, paths_real, paths_min):

        # sort by minimum path length
        paths_min = sorted(paths_min, key=lambda p: self.schedule.get_min_path_delay(p[0]))
        paths_real = sorted(paths_real, key=lambda p: self.schedule.get_min_path_delay(p[0]))

        plt.figure(figsize=(7.5, 4.5))
        x_axis = list(range(1, len(paths_real)+1))

        # plot for mean values
        plt.plot(x_axis, [np.mean(p[1]) for p in paths_real],
                 's-', label=r'$d_p$, avg')

        # plot for average minimum packet delays
        plt.plot(x_axis, [np.mean(p[1]) for p in paths_min],
                 '^-', label=r'$d_{retx}$, avg')

        # plot for minimum path delays
        min_possible_delay = [self.schedule.get_min_path_delay(p[0]) for p in paths_min]
        plt.plot(x_axis, min_possible_delay,
                 '--',
                 label=r'$d_{\min}$', linewidth=3)

        x = range(1, len([str(p[0]) for p in paths_real])+1)
        plt.xticks(x,  [str(list(p[0])+[1]) for p in paths_real])
        locs, labels = plt.xticks()
        plt.setp(labels, rotation=55)

        plt.ylim((-0.02, 0.2))
        plt.grid(True)
        plt.ylabel('delay, s')
        plt.xlabel('path')
        plt.legend(loc=0, fontsize=12, ncol=3)

        # return data for comparison plot

        interf_delay = []
        buffer_delay = []

        for idx, p in enumerate(paths_min):  # take every path
            for i, d in enumerate(p[1]):  # take every packet's delay
                i_delay = (d - self.schedule.get_min_path_delay(p[0]))/len(p[0])
                b_delay = (paths_real[idx][1][i] - d)/len(p[0])
                interf_delay.append(i_delay)
                buffer_delay.append(b_delay)

        return interf_delay, buffer_delay

    def pkt_served_per_mote(self):


        motes = [0 for i in gl_mote_range]

        for pkt in self.packets:
            for hop in pkt.hop_info:
                motes[hop['addr']-1] += 1

        print(motes)
        plt.figure()
        plt.plot(gl_mote_range, motes)

    def plot_path_load(self):
        paths = self.get_all_paths_w_num_pkts()
        print(paths)
        plt.figure()
        plt.plot([p[1] for p in paths])

        x = range(1, len(paths)+1)
        plt.xticks(x,  [str(p[0]) for p in paths])
        locs, labels = plt.xticks()
        plt.setp(labels, rotation=90)


def plot_all_path_delays(shared=False):
    """
    Plot for interference / buffering delay for all scenarios
    :return:
    """

    # create a schedule
    if shared:
        folder = gl_dump_path + '/shared/'
        sched = Schedule(num_slots=gl_num_active_slots, num_off=gl_num_off_slots,
                         num_serial=gl_num_serial_slots, shared=shared)
    else:
        folder = gl_dump_path + '/tdma/'
        sched = Schedule(num_slots=gl_num_active_slots, num_off=gl_num_off_slots, num_serial=gl_num_serial_slots)

    files = [f for f in os.listdir(folder) if isfile(join(folder, f))]
    files = sorted(files)

    int_delays = []
    buf_delays = []

    for idx, filename in enumerate(files):
        if idx == 1:
            # ignore medium interference case
            continue

        p = AdvDelayProcessor(filename=folder + filename, schedule=sched)

        r0, m0 = p.plot_path_delay()

        i, b = p.print_delay(r0, m0)
        int_delays.append(i)
        buf_delays.append(b)

    # comparison figure for different delays
    plt.figure()
    plt.boxplot(int_delays + buf_delays, showmeans=True, showfliers=False)

    x = range(1, 7)
    plt.xticks(x,  ['I (i)', 'III (i)', 'IV (i)', 'I (b)', 'III (b)', 'IV (b)'])
    locs, labels = plt.xticks()
    plt.setp(labels, rotation=0)

    plt.grid(True)
    plt.show()


def plot_intercepting_path_delays(ax, shared=False):
    if shared:
        folder = gl_dump_path + '/shared/'
        sched = Schedule(num_slots=gl_num_active_slots, num_off=gl_num_off_slots,
                         num_serial=gl_num_serial_slots, shared=shared)
    else:
        folder = gl_dump_path + '/tdma/'
        sched = Schedule(num_slots=gl_num_active_slots, num_off=gl_num_off_slots, num_serial=gl_num_serial_slots)

    files = [f for f in os.listdir(folder) if isfile(join(folder, f))]
    files = sorted(files)

    df = pd.DataFrame(columns=['set', 'path', 'real_delay', 'min_delay'])

    for idx, filename in enumerate(files):
        if idx == 1:
            # skip the low interference scenario
            continue

        set_id = idx
        if idx > 0:
            set_id -= 1

        pr = AdvDelayProcessor(filename=folder + filename, schedule=sched)

        r, m = pr.plot_path_delay()

        for i, el in enumerate(r):
            df = df.append({'set': set_id, 'path': el[0], 'real_delay': el[1], 'min_delay': m[i][1]}, ignore_index=True)

    data = df.groupby('path').filter(lambda x: len(x) == 3)

    print(data)

    data['min_path_delay'] = data.path.apply(sched.get_min_path_delay)


    int_delay = [[], [], []]
    buf_delay = [[], [], []]

    for iter in data.iterrows():
        index, d = iter
        int_delay[int(d.set)] += list((np.array(d.min_delay) - d.min_path_delay))#/len(d.path))
        buf_delay[int(d.set)] += list((np.array(d.real_delay) - np.array(d.min_delay)))#/len(d.path))

    bp = ax.boxplot(int_delay + buf_delay, showmeans=True, showfliers=False)
    plt.grid(True)
    set_box_plot(bp)
    # plt.show()
    return


def plot_int_buf_delay():
    fig = plt.figure(figsize=(7.5, 5.225))
    gs = gridspec.GridSpec(2, 1, height_ratios=[1, 1])

    ax0 = fig.add_subplot(gs[0])

    plot_intercepting_path_delays(ax0, shared=False)

    x_axis = list(range(1, 7))
    labels = ['I (l)', 'III (l)', 'IV (l)', 'I (b)', 'III (b)', 'IV (b)']
    plt.xticks(x_axis, labels)
    plt.ylabel('Delay, s')

    ax1 = fig.add_subplot(gs[1])

    plot_intercepting_path_delays(ax1, shared=True)

    labels = ['V (l)', 'VII (l)', 'VIII (l)', 'V (b)', 'VII(b)', 'VIII (b)']
    plt.xticks(x_axis, labels)

    plt.xlabel('Data sets')
    plt.ylabel('Delay, s')
    plt.show()





if __name__ == '__main__':
    plot_all_path_delays(shared=True)
    plt.show()

