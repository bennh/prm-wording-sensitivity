"""Validate formal PRM scores and export paired statistics and publication figures.

Run: python analyze_formal_prm.py
Dependencies: numpy, matplotlib. No model weights or network access are needed.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

ROOT = Path(__file__).resolve().parent
CONDITIONS = ['C-B', 'C-N', 'C-A', 'E-B', 'E-N', 'E-A']
BLUE, ORANGE, INK, GRAY = '#0072B2', '#D55E00', '#25323D', '#B8C1C8'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_and_validate(path):
    payload = json.loads(path.read_text())
    require(payload.get('status') == 'complete', 'Scoring is incomplete.')
    raw = payload['results']
    require(len(raw) == 300, 'Expected exactly 300 score records.')
    data = ROOT / 'data'
    expected = [json.loads(l) for l in (data/'formal_50_variants.jsonl').read_text().splitlines() if l.strip()]
    bases = [json.loads(l) for l in (data/'formal_50.jsonl').read_text().splitlines() if l.strip()]
    dev = {json.loads(l)['problem_id'] for l in (data/'dev_5.jsonl').read_text().splitlines() if l.strip()}
    for name, key in [('formal_50.jsonl','data_sha256'),('formal_50_variants.jsonl','variants_sha256')]:
        require(sha(data/name) == payload['config'][key], f'Source hash mismatch: {name}')
    require(len(expected) == 300 and len(bases) == 50, 'Unexpected source size.')
    groups = {}
    for result, original in zip(raw, expected):
        require(all(result.get(k) == v for k,v in original.items()), 'Scored input differs from the frozen variant.')
        pid, condition = result['problem_id'], result['condition']
        require(pid not in dev and condition in CONDITIONS, 'Invalid split or condition.')
        group = groups.setdefault(pid, {})
        require(condition not in group, 'Duplicate condition.')
        scores = result['step_scores']
        require(isinstance(scores, list) and len(scores) >= 2, 'Expected a nonempty prefix and a target score.')
        require(len(scores) == len(result['steps']) and all(type(s) in (int,float) and np.isfinite(s) and 0 <= s <= 1 for s in scores), 'Invalid step scores.')
        require(result['score'] == scores[-1], 'Target score mismatch.')
        require(result['target_step_index'] == len(scores)-1 and result['target_token_index'] == result['input_tokens']-1, 'Invalid target boundary.')
        require(result['input_tokens'] <= 512, 'Input exceeds frozen token limit.')
        group[condition] = result
    require(len(groups) == 50 and len({r['problem_id'] for r in bases}) == 50, 'Expected 50 distinct questions.')
    require(set(groups) == {r['problem_id'] for r in bases}, 'Score and base-question IDs differ.')
    matrix = []
    prefix_spread = 0.0
    for base in bases:
        g = groups[base['problem_id']]
        require(base.get('split') == 'formal' and bool(base.get('prefix_steps')), 'Invalid formal base record.')
        require(all(r['problem'] == base['problem'] and r['steps'][:-1] == base['prefix_steps'] for r in g.values()), 'Scored problem or prefix differs from the base record.')
        for condition, record in g.items():
            target = base['correct_step'] if condition.startswith('C-') else base['incorrect_step']
            tone = condition[-1]
            expected_target = target if tone == 'B' else {'N': 'For this step, ', 'A': 'Without any doubt, '}[tone] + target[0].lower() + target[1:]
            require(record['steps'][-1] == expected_target, 'Scored target differs from the base record or fixed template.')
        require(set(g) == set(CONDITIONS), 'Missing condition.')
        prefix = [g[c]['step_scores'][:-1] for c in CONDITIONS]
        prefix_spread = max(prefix_spread, float(np.ptp(np.array(prefix),axis=0).max()))
        matrix.append([g[c]['score'] for c in CONDITIONS])
    require(prefix_spread <= 1e-6, 'Shared-prefix scores unexpectedly vary across conditions.')
    return payload, bases, np.asarray(matrix), prefix_spread


def paired_metrics(x):
    cb, cn, ca, eb, en, ea = x.T
    return np.column_stack([ea-en, ca-cn, (cn-en)-(ca-ea), cn-en, ca-ea, cb-eb, en-eb, ea-eb])


METRICS = ['wrong_confidence_effect', 'correct_confidence_effect', 'gap_reduction',
           'neutral_correct_wrong_gap', 'confident_correct_wrong_gap', 'baseline_correct_wrong_gap',
           'wrong_neutral_vs_baseline', 'wrong_confident_vs_baseline']


def estimate(values, indices):
    means = values[indices].mean(axis=1)
    lo, hi = np.quantile(means, [0.025,0.975], axis=0)
    return [{'mean':float(a.mean()), 'median':float(np.median(a)), 'sd':float(a.std(ddof=1)),
             'ci_low':float(l), 'ci_high':float(h), 'positive_count':int((a>0).sum()),
             'negative_count':int((a<0).sum()), 'zero_count':int((a==0).sum())}
            for a,l,h in zip(values.T,lo,hi)]


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def style():
    plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':9, 'axes.labelsize':10,
        'axes.titlesize':11, 'axes.titleweight':'bold', 'axes.titlepad':10,
        'axes.spines.top':False, 'axes.spines.right':False, 'axes.linewidth':0.7,
        'axes.edgecolor':INK, 'text.color':INK, 'axes.labelcolor':INK,
        'xtick.color':INK, 'ytick.color':INK, 'xtick.labelsize':8, 'ytick.labelsize':8,
        'lines.linewidth':1.2, 'pdf.fonttype':42, 'ps.fonttype':42, 'svg.fonttype':'none',
        'savefig.facecolor':'white', 'figure.facecolor':'white'})


def save_figure(fig, directory, name):
    # Fixed physical dimensions: about 180 mm wide for a two-column figure.
    for ext in ['pdf','svg','png']:
        fig.savefig(directory/f'{name}.{ext}', dpi=600 if ext=='png' else 150)
    fig.savefig(directory/f'{name}_preview.png', dpi=140)
    plt.close(fig)


def padded_limits(values, include_zero=False):
    """Include every observation and interval endpoint, even for negative gaps."""
    values = np.asarray(values, dtype=float)
    require(values.size > 0 and np.isfinite(values).all(), 'Invalid axis values.')
    low, high = float(values.min()), float(values.max())
    if include_zero:
        low, high = min(low, 0.0), max(high, 0.0)
    padding = max((high-low)*0.07, 0.005)
    return low-padding, high+padding


def figures(out, matrix, metrics, condition_stats, metric_stats):
    style()
    # Figure 1: common 0-1 scale, different markers for redundant encoding.
    fig, ax = plt.subplots(figsize=(7.1,4.3))
    fig.subplots_adjust(left=.12,right=.97,bottom=.13,top=.88)
    for offset, color, marker, label in [(0,BLUE,'o','Correct step'),(3,ORANGE,'s','Incorrect step')]:
        stats = condition_stats[offset:offset+3]
        y = np.array([s['mean'] for s in stats])
        ax.plot(np.arange(3), y, color=color, marker=marker, ms=6, label=label)
        for i, stat in enumerate(stats):
            ax.vlines(i, stat['ci_low'], stat['ci_high'], color=color, lw=1.2)
            ax.hlines([stat['ci_low'], stat['ci_high']], i-.035, i+.035, color=color, lw=1.2)
    ax.set(xticks=[0,1,2],xticklabels=['Baseline (B)','Neutral (N)','Confident (A)'],ylim=(0,1),xlim=(-.35,2.35),ylabel='Mean PRM score')
    ax.yaxis.set_major_locator(MultipleLocator(.2));ax.grid(axis='y',alpha=.16);ax.set_axisbelow(True)
    ax.legend(frameon=False,loc='upper center',bbox_to_anchor=(.5,1.15),ncol=2)
    save_figure(fig,out,'figure_1_condition_scores')

    # Figure 2: retain every question; ordered by the measured effect for display only.
    fig, ax = plt.subplots(figsize=(7.1,4.5));fig.subplots_adjust(left=.12,right=.97,bottom=.15,top=.96)
    values=metrics[:,0];order=np.argsort(values,kind='stable');sorted_values=values[order];rank=np.arange(1,51)
    for mask,color,marker in [(sorted_values>=0,BLUE,'o'),(sorted_values<0,ORANGE,'v')]:
        ax.vlines(rank[mask],0,sorted_values[mask],color=color,alpha=.65,lw=1)
        ax.scatter(rank[mask],sorted_values[mask],s=20,color=color,marker=marker,zorder=3)
    stat=metric_stats[0]
    ax.axhline(0,color=INK,lw=.85);ax.axhline(stat['mean'],color=GRAY,ls='--',lw=1)
    ax.set(xlim=(0,51),ylim=padded_limits(np.r_[sorted_values, stat['mean']], include_zero=True),xlabel='Question rank (ordered by effect)',ylabel='Incorrect-step score change (A − N)')
    ax.grid(axis='y',alpha=.16);ax.set_axisbelow(True)
    save_figure(fig,out,'figure_2_question_effects')

    # Figure 3: paired gaps and direct uncertainty for the gap reduction.
    fig,(ax,bx)=plt.subplots(1,2,figsize=(7.1,3.9),gridspec_kw={'width_ratios':[1,1.05]})
    fig.subplots_adjust(left=.09,right=.97,bottom=.17,top=.96,wspace=.62)
    gn,ga=metrics[:,3],metrics[:,4]
    gap_limits = padded_limits(np.r_[gn, ga], include_zero=True)
    ax.plot(gap_limits, gap_limits, color=GRAY,ls='--',lw=1,zorder=0)
    ax.scatter(gn,ga,s=22,color=BLUE,edgecolors='white',linewidths=.35,alpha=.85)
    ax.set(xlim=gap_limits,ylim=gap_limits,xlabel='Neutral gap (C−N minus E−N)',ylabel='Confident gap (C−A minus E−A)')
    ax.set_aspect('equal',adjustable='box')
    ax.xaxis.set_major_locator(plt.MaxNLocator(4));ax.yaxis.set_major_locator(plt.MaxNLocator(4))
    labels=['Incorrect score\nA − N','Correct score\nA − N','Gap reduction\nNeutral − confident']
    for i in range(3):
        s=metric_stats[i];color=ORANGE if i==2 else BLUE
        bx.hlines(2-i, s['ci_low'], s['ci_high'], color=color, lw=1.2)
        bx.vlines([s['ci_low'], s['ci_high']], 2-i-.045, 2-i+.045, color=color, lw=1.2)
        bx.plot(s['mean'], 2-i, marker='s' if i==2 else 'o', color=color, ms=5)
    bx.axvline(0,color=GRAY,ls='--',lw=1)
    contrast_limits = padded_limits([s[k] for s in metric_stats[:3] for k in ['mean','ci_low','ci_high']], include_zero=True)
    bx.set(yticks=[2,1,0],yticklabels=labels,ylim=(-.65,2.65),xlim=contrast_limits,xlabel='Mean paired difference')
    bx.xaxis.set_major_locator(plt.MaxNLocator(4))
    bx.spines['left'].set_visible(False);bx.tick_params(axis='y',length=0)
    save_figure(fig,out,'figure_3_gap_robustness')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'results/formal_50_scores.json')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'results/formal_analysis')
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--bootstrap',type=int,default=20000)
    args=parser.parse_args()
    require(args.bootstrap>=1000,'Use at least 1,000 bootstrap replicates.')
    require(args.seed >= 0, 'Seed must be nonnegative.')
    payload,bases,matrix,prefix_spread=load_and_validate(args.input)
    metrics=paired_metrics(matrix)
    # One shared resampling matrix preserves all within-question relationships.
    indices=np.random.default_rng(args.seed).integers(0,50,size=(args.bootstrap,50))
    conditions=estimate(matrix,indices);stats=estimate(metrics,indices)
    for k,s in zip(METRICS,stats):
        if k in payload.get('descriptive_means',{}):
            require(np.isclose(s['mean'],payload['descriptive_means'][k],atol=1e-12,rtol=0),'Stored summary mismatch.')
    out=args.output_dir;out.mkdir(parents=True,exist_ok=True)
    summary={'source_file':str(args.input.resolve()),'source_sha256':sha(args.input),'analysis_script_sha256':sha(Path(__file__)),
        'n_questions':50,'n_inputs':300,'seed':args.seed,'bootstrap_replicates':args.bootstrap,
        'interval_method':'Pointwise 95% percentile bootstrap of question means; paired resampling with replacement',
        'primary_metric':'wrong_confidence_effect','secondary_metric':'gap_reduction',
        'interpretation':'Intervals describe resampling uncertainty in this purposive sample, not benchmark-wide population coverage. Secondary and exploratory intervals are not multiplicity-adjusted. Calibration of PRM scores as correctness probabilities has not been established.',
        'condition_statistics':dict(zip(CONDITIONS,conditions)),'paired_statistics':dict(zip(METRICS,stats)),
        'ranking_inversions':{t:int((matrix[:,i]<matrix[:,i+3]).sum()) for i,t in enumerate('BNA')},
        'ranking_ties':{t:int((matrix[:,i]==matrix[:,i+3]).sum()) for i,t in enumerate('BNA')},
        'validation':{'source_hashes_match':True,'all_conditions_present':True,'shared_prefix_max_score_spread':prefix_spread},
        'versions':{'numpy':np.__version__,'matplotlib':matplotlib.__version__}}
    (out/'analysis_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    write_csv(out/'condition_statistics.csv',[{'condition':k,**v} for k,v in zip(CONDITIONS,conditions)])
    write_csv(out/'paired_statistics.csv',[{'metric':k,**v} for k,v in zip(METRICS,stats)])
    question_rows=[{'formal_id':r['formal_id'],'problem_id':r['problem_id'],'subject':r['subject'],'level':r['level'],**dict(zip(CONDITIONS,map(float,x))),**dict(zip(METRICS,map(float,m)))} for r,x,m in zip(bases,matrix,metrics)]
    write_csv(out/'question_statistics.csv',question_rows)
    write_csv(out/'figure_2_rank_mapping.csv',[{'rank':rank,'formal_id':bases[i]['formal_id'],'problem_id':bases[i]['problem_id'],'wrong_confidence_effect':float(metrics[i,0])} for rank,i in enumerate(np.argsort(metrics[:,0],kind='stable'),1)])
    figures(out,matrix,metrics,conditions,stats)
    lines=['# Formal PRM analysis','', '## Method','',f'All 50 questions and 300 inputs passed validation. Bootstrap: {args.bootstrap:,} question-level paired resamples, seed {args.seed}. Percentile intervals are pointwise, not simultaneous. No model inference was performed.','', '| Contrast | Mean | 95% bootstrap interval |','| --- | ---: | --- |']
    for k,s in zip(METRICS,stats):lines.append(f"| {k} | {s['mean']:+.6f} | [{s['ci_low']:+.6f}, {s['ci_high']:+.6f}] |")
    lines += ['', '## Scope and interpretation', '', 'The primary contrast compares the incorrect target under the confident phrase with the neutral phrase. A positive gap reduction means weaker correct-minus-incorrect separation. A confidence interval crossing zero does not establish equivalence or absence of an effect. A positive incorrect-score effect alone does not establish poorer discrimination.', '', 'This is a purposively selected 50-question sample, one model, one confident phrase, and one +1 arithmetic corruption. Bootstrap uncertainty does not remove selection bias. Generalization to other models, phrases, errors, or all MATH-500 is not established. Primary and secondary contrasts were chosen during project development. This remains an exploratory study, not a preregistered confirmatory test; all reported intervals are pointwise and are not adjusted for multiple comparisons. Scores are not treated as calibrated correctness probabilities.', '', 'The A-minus-N contrast estimates replacement of one fixed neutral phrase by one fixed confident phrase, not a general causal effect of confidence. Equal token lengths remove a length difference for these inputs but do not remove lexical or stylistic confounding. Comparison with the baseline must remain distinct from the main A-minus-N comparison. This experiment does not measure downstream answer harm, error severity, or performance on complete generated reasoning traces.', '', '## Figure captions', '', 'Figure 1. Mean PRM scores for correct and incorrect steps under baseline, neutral, and confident wording. Error bars show pointwise 95% question-bootstrap intervals. Differences must be assessed using paired contrasts, not overlap of these marginal intervals.', '', 'Figure 2. Incorrect-step score changes (confident minus neutral) for all 50 questions, sorted only for visualization. The dashed line marks the mean. Rank-to-question correspondence is provided separately.', '', 'Figure 3. Left: correct-minus-incorrect score gaps under neutral and confident wording; the diagonal indicates equality. Right: mean paired contrasts with pointwise 95% bootstrap intervals. Positive gap reduction denotes narrower separation under confident wording.', '', '## Export specifications', '', 'Figures are 7.1 inches wide (about 180 mm), with 8–11 pt typography, redundant shape/color encoding, white backgrounds, and no decorative effects. PDF uses embedded TrueType fonts; SVG preserves editable text; PNG is exported at 600 dpi. Use PDF for manuscript layout and adapt dimensions to the target journal. No journal-specific compliance is claimed. Preview PNG files are for inspection only. Figure titles, explanatory notes, and point-value annotations are omitted from the artwork; captions belong in the manuscript.', '', '## Illustrative cases', '', 'The following extrema are selected deterministically to show both directions. They are illustrations, not representative estimates.']
    for label,i in [('Largest increase',int(np.argmax(metrics[:,0]))),('Largest decrease',int(np.argmin(metrics[:,0])))]:
        r=bases[i];lines += ['',f"### {label}: {r['formal_id']}",'',f"Source: {r['problem_id']}",'',r['problem'],'',f"Incorrect target: {r['incorrect_step']}",'',f"E-N = {matrix[i,4]:.6f}; E-A = {matrix[i,5]:.6f}; difference = {metrics[i,0]:+.6f}."]
    (out/'analysis_report.md').write_text('\n'.join(lines)+'\n')
    print(f'Validated 50 questions / 300 inputs. Outputs: {out.resolve()}')
    for k,s in zip(METRICS[:3],stats[:3]):print(f"{k}: {s['mean']:+.6f} [{s['ci_low']:+.6f}, {s['ci_high']:+.6f}]")


if __name__=='__main__':
    main()
