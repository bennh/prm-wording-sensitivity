# Formal PRM analysis

## Method

All 50 questions and 300 inputs passed validation. Bootstrap: 20,000 question-level paired resamples, seed 42. Percentile intervals are pointwise, not simultaneous. No model inference was performed.

| Contrast | Mean | 95% bootstrap interval |
| --- | ---: | --- |
| wrong_confidence_effect | +0.014320 | [-0.001933, +0.031023] |
| correct_confidence_effect | +0.016526 | [+0.005497, +0.027639] |
| gap_reduction | -0.002206 | [-0.022341, +0.018261] |
| neutral_correct_wrong_gap | +0.431130 | [+0.378005, +0.483644] |
| confident_correct_wrong_gap | +0.433336 | [+0.385772, +0.479982] |
| baseline_correct_wrong_gap | +0.469946 | [+0.417073, +0.521133] |
| wrong_neutral_vs_baseline | +0.009162 | [-0.004822, +0.023048] |
| wrong_confident_vs_baseline | +0.023482 | [+0.009612, +0.038036] |

## Scope and interpretation

The primary contrast compares the incorrect target under the confident phrase with the neutral phrase. A positive gap reduction means weaker correct-minus-incorrect separation. A confidence interval crossing zero does not establish equivalence or absence of an effect. A positive incorrect-score effect alone does not establish poorer discrimination.

This is a purposively selected 50-question sample, one model, one confident phrase, and one +1 arithmetic corruption. Bootstrap uncertainty does not remove selection bias. Generalization to other models, phrases, errors, or all MATH-500 is not established. Primary and secondary contrasts were chosen during project development. This remains an exploratory study, not a preregistered confirmatory test; all reported intervals are pointwise and are not adjusted for multiple comparisons. Scores are not treated as calibrated correctness probabilities.

The A-minus-N contrast estimates replacement of one fixed neutral phrase by one fixed confident phrase, not a general causal effect of confidence. Equal token lengths remove a length difference for these inputs but do not remove lexical or stylistic confounding. Comparison with the baseline must remain distinct from the main A-minus-N comparison. This experiment does not measure downstream answer harm, error severity, or performance on complete generated reasoning traces.

## Figure captions

Figure 1. Mean PRM scores for correct and incorrect steps under baseline, neutral, and confident wording. Error bars show pointwise 95% question-bootstrap intervals. Differences must be assessed using paired contrasts, not overlap of these marginal intervals.

Figure 2. Incorrect-step score changes (confident minus neutral) for all 50 questions, sorted only for visualization. The dashed line marks the mean. Rank-to-question correspondence is provided separately.

Figure 3. Left: correct-minus-incorrect score gaps under neutral and confident wording; the diagonal indicates equality. Right: mean paired contrasts with pointwise 95% bootstrap intervals. Positive gap reduction denotes narrower separation under confident wording.

## Export specifications

Figures are 7.1 inches wide (about 180 mm), with 8–11 pt typography, redundant shape/color encoding, white backgrounds, and no decorative effects. PDF uses embedded TrueType fonts; SVG preserves editable text; PNG is exported at 600 dpi. Use PDF for manuscript layout and adapt dimensions to the target journal. No journal-specific compliance is claimed. Preview PNG files are for inspection only. Figure titles, explanatory notes, and point-value annotations are omitted from the artwork; captions belong in the manuscript.

## Illustrative cases

The following extrema are selected deterministically to show both directions. They are illustrations, not representative estimates.

### Largest increase: formal_018

Source: test/prealgebra/1922.json

Two-thirds of the students at Baker Middle School take music. There are 834 students who take music. How many students are there at Baker Middle School?

Incorrect target: The numerator is 3 * 834 = 2503.

E-N = 0.304704; E-A = 0.494185; difference = +0.189481.

### Largest decrease: formal_039

Source: test/algebra/2743.json

Three pencils and a jumbo eraser cost $\$1.24$. Five pencils and a jumbo eraser cost $\$1.82$. No prices include tax. In cents, what is the cost of a pencil?

Incorrect target: The difference in total costs is 182 - 124 = 59 cents.

E-N = 0.599631; E-A = 0.421031; difference = -0.178600.
