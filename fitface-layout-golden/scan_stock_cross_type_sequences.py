#!/usr/bin/env python3
"""Prove whether one live sequence is consumed by multiple widget types in Samsung stock faces."""

from __future__ import annotations

import concurrent.futures
import json
import pathlib

import scan_stock_weather_locale_candidates as stock


def analyze(face):
    try:
        container = stock.download(face)
        entries = stock.directory(container)
        hits = []
        for path, data in entries:
            name = pathlib.Path(path).name
            if not name.startswith('style') or not name.endswith('.bin'):
                continue
            records = stock.scan_widgets(data)
            by_seq = {}
            for record in records:
                by_seq.setdefault(record['seq'], []).append(record)
            for sequence, members in by_seq.items():
                types = sorted(set(member['type'] for member in members))
                if len(types) > 1:
                    hits.append({
                        'style': name,
                        'sequence': sequence,
                        'types': types,
                        'records': [
                            {'g': member['g'], 'type': member['type'], 'words': member['words']}
                            for member in members
                        ],
                    })
        return {
            'face': face['face'],
            'name': face['name'],
            'hits': hits,
        }
    except Exception as error:
        return {'face': face['face'], 'name': face['name'], 'error': repr(error), 'hits': []}


def main():
    faces = stock.catalog()
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for result in pool.map(analyze, faces):
            if result['hits']:
                results.append(result)
    results.sort(key=lambda item: item['face'])
    total_hits = sum(len(item['hits']) for item in results)
    print(f'CROSS_TYPE_FACE_COUNT={len(results)}')
    print(f'CROSS_TYPE_HIT_COUNT={total_hits}')
    sprite_pair = []
    for item in results:
        for hit in item['hits']:
            if 3 in hit['types'] and 5 in hit['types']:
                sprite_pair.append({'face': item['face'], 'name': item['name'], **hit})
    print(f'SPRITE_PAIR_SHARED_SEQUENCE_COUNT={len(sprite_pair)}')
    for hit in sprite_pair[:50]:
        print('SPRITE_PAIR_SHARED_SEQUENCE_JSON=' + json.dumps(hit, ensure_ascii=False, separators=(',', ':')))
    if not sprite_pair:
        raise SystemExit('no stock Sprite+Pair shared-sequence precedent found')


if __name__ == '__main__':
    main()
