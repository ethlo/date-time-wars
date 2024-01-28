#!/usr/bin/env python3

import argparse
import json


def extract_data(source_path):
    with open(source_path) as json_data:
        arr = json.load(json_data)
        for e in arr:
            benchmark_class_and_method = e.get("benchmark")
            test_name = benchmark_class_and_method.split('.')[1]
            method_name = benchmark_class_and_method.rsplit('.', 1)[-1]
            e['benchmark'] = method_name + "." + test_name

        def extract_time(d):
            try:
                return int(d['primaryMetric']['score'])
            except KeyError:
                return 0

        arr.sort(key=extract_time, reverse=False)
        return arr


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='ReportGenerator')
    parser.add_argument('-i', default='jmh-result.json', help='The JMH result (JSON) file')
    args = vars(parser.parse_args())
    data = extract_data(args.get('i'))
    with open('jmh-result-grouped.json', "w") as f:
        f.write(json.dumps(data, indent=2))
