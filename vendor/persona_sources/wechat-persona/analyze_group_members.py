#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_group_members.py — 对 export_group.py 输出的每位成员
跑 stats + sampler,生成 personality_input.json,等待 LLM 填写结果。
"""

import argparse
import json
import os
import sys
from pathlib import Path

import data_loader
import sampler
import stats as stats_mod
from personality import extract_features


def analyze_member(member_dir: Path, sample_size: int = 100):
    csv_files = list(member_dir.glob('*.csv'))
    if not csv_files:
        print(f'  ⚠️  {member_dir.name} 无 CSV,跳过')
        return None
    csv_path = csv_files[0]

    df = data_loader.load(str(csv_path), sender=1)
    if len(df) == 0:
        print(f'  ⚠️  {member_dir.name} 加载后无消息,跳过')
        return None

    stats = stats_mod.compute(df)
    dr = stats['date_range']

    clean_df = data_loader.filter_for_personality(df)
    messages = sampler.smart_sample(clean_df, target_n=sample_size)
    features = extract_features(messages)
    top_words = sorted(stats['word_freq'].items(), key=lambda x: x[1], reverse=True)[:30]

    ai_input = {
        'sample_messages': messages,
        'top_words': [{'word': w, 'count': c} for w, c in top_words],
        'features': features,
        'stats_summary': {
            'date_range': [dr[0].strftime('%Y-%m-%d'), dr[1].strftime('%Y-%m-%d')],
            'total_messages': stats['total_messages'],
            'avg_length': stats['avg_length'],
            'most_active_hour': int(stats['hourly'].idxmax()),
        },
    }
    out_path = member_dir / 'personality_input.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(ai_input, f, ensure_ascii=False, indent=2)
    print(f'  ✓ {member_dir.name}: {len(df)} 条 → 采样 {len(messages)} 条 → {out_path.name}')
    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('group_dir', help='export_group.py 输出目录')
    parser.add_argument('--sample-size', type=int, default=100)
    args = parser.parse_args()

    group_dir = Path(args.group_dir)
    overview_path = group_dir / 'group_overview.json'
    if not overview_path.exists():
        print(f'❌ 找不到 group_overview.json: {overview_path}')
        sys.exit(1)
    with open(overview_path, encoding='utf-8') as f:
        overview = json.load(f)

    print(f'[*] 群: {overview["group_name"]}')
    for m in overview['top_members']:
        slug = m['slug']
        member_dir = group_dir / slug
        if not member_dir.exists():
            continue
        analyze_member(member_dir, sample_size=args.sample_size)


if __name__ == '__main__':
    main()
