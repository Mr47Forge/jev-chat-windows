#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
group_report.py — 把 export_group + analyze_group_members + 人格 JSON
拼成一份"群友 N 连画像"HTML 报告。
"""

import argparse
import base64
import json
import os
import sys
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import data_loader
import stats as stats_mod
import visualizer
from visualizer import (
    BROWN_DARK, BROWN_MID, BROWN_LIGHT, BROWN_PALE, CREAM, CHART_BG,
    TEXT_DARK, TEXT_MID, TEAL_DARK, TEAL_MID, _style,
)

MEMBER_COLORS = ['#1B4332', '#C7522A', '#2C5F7C', '#7B5C8E', '#5C9479']


def avatar_b64(path):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, 'rb') as f:
            data = f.read()
        if data[:4] == b'\x89PNG':
            mime = 'image/png'
        elif data[:3] == b'\xff\xd8\xff':
            mime = 'image/jpeg'
        else:
            mime = 'image/jpeg'
        return f"data:{mime};base64,{base64.b64encode(data).decode()}"
    except Exception:
        return None


def png_b64(path):
    if not os.path.exists(path):
        return ''
    with open(path, 'rb') as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"


def member_share_pie(members, output_path):
    """4 人发言量的玫瑰图(甜甜圈)。"""
    labels = [m['name'] for m in members]
    values = [m['message_count'] for m in members]
    colors = MEMBER_COLORS[: len(members)]

    fig, ax = plt.subplots(figsize=(7, 6), facecolor=CHART_BG)
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=colors,
        autopct='%1.1f%%', startangle=90,
        wedgeprops=dict(width=0.45, edgecolor=CHART_BG, linewidth=3),
        pctdistance=0.78,
        textprops=dict(color=TEXT_DARK, fontsize=11),
    )
    for at in autotexts:
        at.set_color('white'); at.set_fontweight('bold'); at.set_fontsize(10)

    ax.set_title('群里谁话最多?', fontsize=14, fontweight='bold', color=TEXT_DARK, pad=18)
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=CHART_BG)
    plt.close(fig)


def group_daily_stack(per_member_dfs, member_names, output_path):
    """4 人按日发言量堆叠。"""
    # 合并所有日期
    all_dates = sorted({d for df in per_member_dfs for d in df['date'].unique()})
    if not all_dates:
        return
    idx = pd.to_datetime(all_dates)
    daily = pd.DataFrame(index=idx)
    for df, name in zip(per_member_dfs, member_names):
        s = df.groupby('date').size()
        s.index = pd.to_datetime(s.index)
        daily[name] = s.reindex(idx, fill_value=0)

    fig, ax = plt.subplots(figsize=(13, 4.5), facecolor=CHART_BG)
    bottom = np.zeros(len(daily))
    for i, name in enumerate(member_names):
        vals = daily[name].values
        ax.fill_between(daily.index, bottom, bottom + vals,
                        color=MEMBER_COLORS[i], alpha=0.85, label=name, linewidth=0)
        bottom = bottom + vals

    _style(ax, title='群里每天的热闹程度(按发言人堆叠)', ylabel='消息数')
    ax.legend(loc='upper left', frameon=False, fontsize=9)
    fig.autofmt_xdate(rotation=30)
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=CHART_BG)
    plt.close(fig)


def group_wordcloud(all_word_freq, output_path):
    from visualizer import _make_wordcloud
    if not all_word_freq:
        return
    wc = _make_wordcloud(all_word_freq, colormap='YlOrBr', width=1000, height=420)
    fig, ax = plt.subplots(figsize=(13, 5.5), facecolor=CREAM)
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off')
    ax.set_title('全群的高频词', fontsize=14, fontweight='bold', color=TEXT_DARK, pad=10)
    fig.patch.set_facecolor(CREAM)
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=CREAM)
    plt.close(fig)


def member_radar(scores, color, output_path):
    """单成员 Big5 雷达图(支持自定义色)。"""
    labels = ['开放性', '尽责性', '外倾性', '宜人性', '神经质']
    keys = ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']
    vals = [scores.get(k, 50) / 100 for k in keys]
    N = len(labels)
    angles = [n / N * 2 * np.pi for n in range(N)] + [0]
    vals = vals + vals[:1]

    fig, ax = plt.subplots(figsize=(4.4, 4.4), subplot_kw=dict(polar=True), facecolor=CHART_BG)
    ax.set_facecolor(CHART_BG)
    ax.fill(angles, vals, alpha=0.30, color=color)
    ax.plot(angles, vals, color=color, linewidth=2)
    ax.scatter(angles[:-1], vals[:-1], s=40, color=color, zorder=5)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=8, color=TEXT_DARK)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8])
    ax.set_yticklabels(['20', '40', '60', '80'], size=6, color=TEXT_MID)
    ax.set_ylim(0, 1)
    ax.grid(color=BROWN_PALE, linestyle='--', alpha=0.5)
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=CHART_BG)
    plt.close(fig)


def group_radar_compare(member_scores, member_names, output_path):
    """4 人 Big5 雷达图叠加。"""
    labels = ['开放性', '尽责性', '外倾性', '宜人性', '神经质']
    keys = ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']
    N = len(labels)
    angles = [n / N * 2 * np.pi for n in range(N)] + [0]

    fig, ax = plt.subplots(figsize=(7.5, 7.5), subplot_kw=dict(polar=True), facecolor=CHART_BG)
    ax.set_facecolor(CHART_BG)

    for i, (scores, name) in enumerate(zip(member_scores, member_names)):
        vals = [scores.get(k, 50) / 100 for k in keys]
        vals = vals + vals[:1]
        ax.plot(angles, vals, color=MEMBER_COLORS[i], linewidth=2, label=name)
        ax.fill(angles, vals, alpha=0.10, color=MEMBER_COLORS[i])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=10, color=TEXT_DARK)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8])
    ax.set_yticklabels(['20', '40', '60', '80'], size=7, color=TEXT_MID)
    ax.set_ylim(0, 1)
    ax.grid(color=BROWN_PALE, linestyle='--', alpha=0.5)
    ax.set_title('四人 Big5 对比', fontsize=14, fontweight='bold', color=TEXT_DARK, pad=22)
    ax.legend(loc='upper right', bbox_to_anchor=(1.28, 1.10), fontsize=10, frameon=False)
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=CHART_BG)
    plt.close(fig)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{group_name} · WeChat Persona</title>
<style>
  :root {{
    --green-900: #1B4332;
    --green-700: #2D6A4F;
    --green-500: #356B52;
    --green-300: #95B6A4;
    --green-100: #DCE9E1;
    --green-050: #F0F6F2;
    --amber-700: #A8742C;
    --amber-500: #D4A24C;
    --amber-100: #F2E2C2;
    --bg: #FAFCFB;
    --surface: #FFFFFF;
    --surface-2: #F4F7F5;
    --text: #15241D;
    --text-mid: #4A5C53;
    --text-soft: #8A988F;
    --line: #E1E8E3;
    --mono: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', system-ui, sans-serif;
    background: var(--bg); color: var(--text); margin: 0; padding: 0;
    line-height: 1.6;
  }}
  .container {{ max-width: 1080px; margin: 0 auto; padding: 36px 32px 60px; }}

  /* ── Header ── */
  .topbar {{
    display: flex; align-items: baseline; justify-content: space-between;
    border-bottom: 1px solid var(--line);
    padding-bottom: 14px; margin-bottom: 28px;
  }}
  .brandmark {{
    font-family: var(--mono); font-size: 13px;
    color: var(--green-700); letter-spacing: .14em; font-weight: 600;
  }}
  .doc-tag {{
    font-family: var(--mono); font-size: 11px; color: var(--text-soft);
    letter-spacing: .08em;
  }}

  h1 {{
    font-size: 28px; color: var(--green-900); margin: 0 0 6px;
    font-weight: 600; letter-spacing: .02em;
  }}
  h1::before {{
    content: '⬢ '; color: var(--green-700); font-weight: 400;
    margin-right: 2px;
  }}
  .subtitle {{
    color: var(--text-mid); margin: 0 0 32px;
    font-size: 13px; font-family: var(--mono); letter-spacing: .02em;
  }}
  .subtitle span {{ color: var(--text); font-weight: 600; }}

  h2 {{
    font-size: 16px; color: var(--green-900); margin: 40px 0 16px;
    border-left: 3px solid var(--green-700);
    padding: 0 0 8px 12px;
    border-bottom: 1px solid var(--line);
    letter-spacing: .04em; font-weight: 600;
  }}

  /* ── Stats row ── */
  .stats-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 18px 0 24px; }}
  .stat-card {{
    background: var(--surface); padding: 18px 18px 16px;
    border: 1px solid var(--line);
    position: relative;
  }}
  .stat-card::after {{
    content: ''; position: absolute; left: 0; right: 0; bottom: 0;
    height: 2px; background: var(--green-700);
  }}
  .stat-label {{
    font-size: 11px; color: var(--text-soft);
    text-transform: uppercase; letter-spacing: .08em;
    font-family: var(--mono);
  }}
  .stat-value {{
    font-size: 26px; color: var(--green-900); font-weight: 600;
    margin-top: 6px; font-family: var(--mono); letter-spacing: -.02em;
  }}

  img.chart {{
    width: 100%; max-width: 1000px; margin: 14px 0;
    border: 1px solid var(--line); background: var(--surface);
  }}

  /* ── Member card ── */
  .member-card {{
    background: var(--surface); border: 1px solid var(--line);
    padding: 24px 28px; margin: 18px 0;
    position: relative;
  }}
  .member-card::before {{
    content: ''; position: absolute; left: 0; top: 0; bottom: 0;
    width: 3px; background: var(--green-700);
  }}
  .member-header {{ display: flex; align-items: center; gap: 18px; margin-bottom: 14px; }}
  .avatar, .avatar-fallback {{
    width: 56px; height: 56px;
    border: 1px solid var(--line);
    background: var(--surface-2);
  }}
  .avatar {{ object-fit: cover; }}
  .avatar-fallback {{
    background: var(--green-700); color: white; display: flex;
    align-items: center; justify-content: center;
    font-size: 22px; font-weight: 600; font-family: var(--mono);
  }}
  .member-title h3 {{
    margin: 0; font-size: 20px; color: var(--green-900); font-weight: 600;
  }}
  .member-meta {{
    font-size: 11px; color: var(--text-soft); margin-top: 4px;
    font-family: var(--mono); letter-spacing: .04em;
  }}
  .one-line {{
    background: var(--green-050);
    border-left: 3px solid var(--amber-500);
    padding: 12px 16px; font-size: 15px; color: var(--text);
    margin: 12px 0;
  }}
  .summary {{ font-size: 14px; line-height: 1.8; color: var(--text-mid); margin: 12px 0; }}
  .row {{ display: flex; gap: 24px; flex-wrap: wrap; align-items: flex-start; }}
  .col-left {{ flex: 1.4; min-width: 300px; }}
  .col-right {{ flex: 1; min-width: 220px; text-align: center; }}
  .col-right img {{ max-width: 280px; border: none; }}

  /* ── Big5 bars ── */
  .big5 {{ margin: 14px 0; }}
  .big5-row {{
    display: flex; align-items: center; margin: 7px 0; gap: 12px;
    font-size: 12px; font-family: var(--mono);
  }}
  .big5-label {{ width: 60px; color: var(--text-soft); letter-spacing: .04em; }}
  .big5-bar {{
    flex: 1; background: var(--green-100); height: 6px;
    overflow: hidden;
  }}
  .big5-bar-fill {{ height: 100%; background: var(--green-700); }}
  .big5-score {{
    width: 30px; text-align: right; color: var(--green-900);
    font-weight: 600; letter-spacing: -.02em;
  }}

  /* ── MBTI ── */
  .mbti-badge {{
    display: inline-block; padding: 3px 10px; background: transparent;
    color: var(--green-700); border: 1px solid var(--green-700);
    font-size: 12px; font-weight: 600; font-family: var(--mono);
    letter-spacing: .12em; margin-left: 10px;
  }}
  .mbti-note {{
    font-size: 12px; color: var(--text-soft); margin: 8px 0;
    line-height: 1.65; font-style: italic;
  }}

  /* ── Lists ── */
  .strengths, .funfacts {{ margin: 6px 0 0; padding-left: 18px; font-size: 13px; }}
  .strengths li, .funfacts li {{ margin: 4px 0; color: var(--text-mid); line-height: 1.6; }}
  .label-tag {{
    display: inline-block; font-size: 10px; color: var(--text-soft);
    letter-spacing: .12em; text-transform: uppercase;
    margin-top: 14px; font-family: var(--mono); font-weight: 600;
  }}

  /* ── Reliability + Footer ── */
  .reliability {{
    margin-top: 36px; padding: 16px 20px;
    background: var(--surface-2);
    border-left: 3px solid var(--amber-500);
    font-size: 12px; color: var(--text-mid); line-height: 1.75;
  }}
  .reliability strong {{ color: var(--green-900); }}
  .footer {{
    margin-top: 48px; padding-top: 18px;
    border-top: 1px solid var(--line);
    text-align: center; font-family: var(--mono);
  }}
  .footer .brand {{
    color: var(--green-700); font-size: 14px; font-weight: 600;
    letter-spacing: .14em;
  }}
  .footer .credit {{
    color: var(--text-soft); font-size: 11px; margin-top: 6px;
    letter-spacing: .04em;
  }}
</style>
</head>
<body>
<div class="container">
  <div class="topbar">
    <div class="brandmark">⬢ WeChat Persona</div>
    <div class="doc-tag">GROUP REPORT · v1</div>
  </div>

  <h1>{group_name}</h1>
  <p class="subtitle">群友 <span>{n_members}</span> 连画像 · 数据范围 <span>{date_from} → {date_to}</span> · 共 <span>{total_msg:,}</span> 条消息</p>

  <h2>群级总览 / Group Overview</h2>
  <div class="stats-row">
    <div class="stat-card"><div class="stat-label">total msgs</div><div class="stat-value">{total_msg:,}</div></div>
    <div class="stat-card"><div class="stat-label">members</div><div class="stat-value">{n_members}</div></div>
    <div class="stat-card"><div class="stat-label">duration</div><div class="stat-value">{n_days}d</div></div>
    <div class="stat-card"><div class="stat-label">top sender</div><div class="stat-value" style="font-size:18px">{top_name}</div></div>
  </div>

  <img class="chart" src="{share_pie}" alt="发言占比">
  <img class="chart" src="{daily_stack}" alt="每日活跃度">
  <img class="chart" src="{group_wc}" alt="全群词云">
  <img class="chart" src="{compare_radar}" alt="四人 Big5 对比">

  <h2>群友画像 / Member Profiles</h2>
  {member_cards}

  <div class="reliability">
    <strong>关于本报告</strong><br>
    本报告基于群聊样本生成,人格判断仅作参考。每位成员的 Big5/MBTI 见各自卡片下方说明。
    群聊语境与一对一不同,同一个人在不同场景下的表现差异可能很大——这正是 MBTI 字母分类的固有局限。
  </div>

  <div class="footer">
    <div class="brand">⬢ WeChat Persona</div>
    <div class="credit">Forked from 姜饼探AI by lewer · {date_from} → {date_to}</div>
  </div>
</div>
</body>
</html>
"""


MEMBER_CARD_TEMPLATE = """
<div class="member-card">
  <div class="member-header">
    {avatar_html}
    <div class="member-title">
      <h3>{name}{self_marker}<span class="mbti-badge">{mbti_type}</span></h3>
      <div class="member-meta">{count:,} 条消息 · 占群 {pct:.1f}% · MBTI 置信度 {mbti_conf}</div>
    </div>
  </div>
  <div class="one-line">{one_line}</div>
  <div class="row">
    <div class="col-left">
      <div class="summary">{summary}</div>
      <div class="big5">{big5_bars}</div>
      <div class="mbti-note">{mbti_note}</div>
      <div><strong style="color: var(--text-mid); font-size: 12px;">优势/亮点</strong>
        <ul class="strengths">{strengths_html}</ul>
      </div>
      <div><strong style="color: var(--text-mid); font-size: 12px;">趣味发现</strong>
        <ul class="funfacts">{funfacts_html}</ul>
      </div>
    </div>
    <div class="col-right">
      <img src="{radar_b64}" alt="Big5 雷达">
    </div>
  </div>
</div>
"""


def big5_bars_html(big5):
    keys = ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']
    label_map = {
        'openness': '开放', 'conscientiousness': '尽责', 'extraversion': '外倾',
        'agreeableness': '宜人', 'neuroticism': '神经质',
    }
    rows = []
    for k in keys:
        score = big5.get(k, {}).get('score', 50)
        rows.append(
            f'<div class="big5-row">'
            f'<span class="big5-label">{label_map[k]}</span>'
            f'<div class="big5-bar"><div class="big5-bar-fill" style="width:{score}%"></div></div>'
            f'<span class="big5-score">{score}</span>'
            f'</div>'
        )
    return ''.join(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('group_dir', help='export_group.py 输出目录')
    parser.add_argument('--output', default=None, help='输出 HTML 路径(默认 <group_dir>/group_report.html)')
    args = parser.parse_args()

    group_dir = Path(args.group_dir)
    overview_path = group_dir / 'group_overview.json'
    if not overview_path.exists():
        print(f'❌ {overview_path} 不存在'); sys.exit(1)
    overview = json.load(open(overview_path, encoding='utf-8'))

    visualizer.setup_font()

    charts_dir = group_dir / 'charts'
    charts_dir.mkdir(exist_ok=True)

    members = overview['top_members']
    member_dfs = []
    member_names = []
    member_results = []
    member_meta = []
    all_word_freq: Counter = Counter()

    for m in members:
        slug = m['slug']
        sub = group_dir / slug
        csv_path = sub / f'{slug}.csv'
        df = data_loader.load(str(csv_path), sender=1)
        s = stats_mod.compute(df)
        all_word_freq += s['word_freq']

        result_path = sub / 'personality_result.json'
        if not result_path.exists():
            print(f'⚠️  {slug} 缺人格结果,跳过此成员')
            continue
        result = json.load(open(result_path, encoding='utf-8'))

        # 单人 radar
        big5 = result.get('big5', {})
        scores = {k: v.get('score', 50) for k, v in big5.items()}
        radar_path = charts_dir / f'radar_{slug}.png'
        member_radar(scores, MEMBER_COLORS[len(member_results)], radar_path)

        member_dfs.append(df)
        member_names.append(m['name'])
        member_results.append(result)
        member_meta.append(m)

    # 群级图表
    share_pie_path = charts_dir / 'share_pie.png'
    daily_stack_path = charts_dir / 'daily_stack.png'
    group_wc_path = charts_dir / 'group_wordcloud.png'
    compare_radar_path = charts_dir / 'compare_radar.png'

    member_share_pie(member_meta, share_pie_path)
    group_daily_stack(member_dfs, member_names, daily_stack_path)
    group_wordcloud(all_word_freq, group_wc_path)
    group_radar_compare(
        [{k: v.get('score', 50) for k, v in r.get('big5', {}).items()} for r in member_results],
        member_names, compare_radar_path,
    )

    # 渲染成员卡片
    cards = []
    total_count = sum(m['message_count'] for m in member_meta)
    for m, result, df in zip(member_meta, member_results, member_dfs):
        avatar_data = avatar_b64(get_avatar_meta(group_dir / m['slug'], 'self_avatar_path'))
        if avatar_data:
            avatar_html = f'<img class="avatar" src="{avatar_data}" alt="">'
        else:
            initial = m['name'][0] if m['name'] else '?'
            avatar_html = f'<div class="avatar-fallback">{initial}</div>'
        radar_data = png_b64(charts_dir / f"radar_{m['slug']}.png")
        big5 = result.get('big5', {})
        mbti = result.get('mbti', {})
        style_block = result.get('style', {})
        cards.append(MEMBER_CARD_TEMPLATE.format(
            name=m['name'],
            self_marker=' (你)' if m['is_self'] else '',
            mbti_type=mbti.get('type', '?'),
            count=m['message_count'],
            pct=m['message_count'] / total_count * 100,
            mbti_conf=mbti.get('confidence', '?'),
            one_line=style_block.get('one_line', ''),
            summary=style_block.get('summary', ''),
            big5_bars=big5_bars_html(big5),
            mbti_note=mbti.get('note', ''),
            strengths_html=''.join(f'<li>{s}</li>' for s in style_block.get('strengths', [])),
            funfacts_html=''.join(f'<li>{s}</li>' for s in style_block.get('fun_facts', [])),
            avatar_html=avatar_html,
            radar_b64=radar_data,
        ))

    n_days = (pd.to_datetime(overview['date_range'][1]) - pd.to_datetime(overview['date_range'][0])).days + 1
    top_name = max(member_meta, key=lambda x: x['message_count'])['name']

    html = HTML_TEMPLATE.format(
        group_name=overview['group_name'],
        n_members=len(member_meta),
        date_from=overview['date_range'][0],
        date_to=overview['date_range'][1],
        total_msg=overview['message_count'],
        n_days=n_days,
        top_name=top_name,
        share_pie=png_b64(share_pie_path),
        daily_stack=png_b64(daily_stack_path),
        group_wc=png_b64(group_wc_path),
        compare_radar=png_b64(compare_radar_path),
        member_cards=''.join(cards),
    )

    out_path = Path(args.output) if args.output else group_dir / 'group_report.html'
    out_path.write_text(html, encoding='utf-8')
    print(f'✅ 群友画像报告生成: {out_path}')


def get_avatar_meta(member_dir: Path, key: str):
    """从成员目录里的 .meta.json 拿头像路径。"""
    for p in member_dir.glob('*.meta.json'):
        try:
            meta = json.load(open(p, encoding='utf-8'))
            return meta.get(key)
        except Exception:
            return None
    return None


if __name__ == '__main__':
    main()
