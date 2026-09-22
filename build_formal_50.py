"""Construct paired formal inputs without loading or scoring a model."""

import argparse
import ast
import hashlib
import json
import operator
import sys
from pathlib import Path

TEMPLATES = {'B': '{step}', 'N': 'For this step, {step}', 'A': 'Without any doubt, {step}'}
REVISION = '98d69606595eedbdbbbf0a7d28efdcd462ba6a67'
MODEL_ID = 'Skywork/Skywork-o1-Open-PRM-Qwen-2.5-1.5B'
# Prefixes contain only valid reasoning up to, but not including, the target result.
# Result placeholders guarantee that each error changes exactly one integer.
CONSTRUCTIONS = [
('Substitute x = -2 into f(x). The numerator is 3 * (-2) - 2.', 'The product 3 * (-2) is {result}.'),
('The distance formula uses the differences between corresponding coordinates. The horizontal difference is 2 - (-4).', 'The horizontal difference is 2 - (-4) = {result}.'),
('Distribute 6 over 1 + 2i. The coefficient of i in this product is 2 * 6.', 'The coefficient from this multiplication is 2 * 6 = {result}.'),
('The profit is the total sales revenue minus the baking cost. Calculate the revenue from the 20 cupcakes sold at 2 dollars each.', 'The cupcake revenue is 20 * 2 = {result} dollars.'),
('To convert 3/20 to a decimal, multiply both the numerator and the denominator by 5.', 'The new numerator is 3 * 5 = {result}.'),
('Factor the first two terms to write 99^2 + 99 + 1 as 99(99 + 1) + 1.', 'The sum inside the parentheses is 99 + 1 = {result}.'),
('Subtract the students in neither club from the class total to count those in at least one club.', 'The number in at least one club is 50 - 6 = {result}.'),
('An outfit is determined by a shirt, a pair of pants, and a hat. First count the combinations of a shirt and a pair of pants.', 'The number of shirt-pants combinations is 5 * 6 = {result}.'),
('Remove the parentheses and group like terms: (-k + 3k) + (4 - 2).', 'The constant term is 4 - 2 = {result}.'),
('Use the difference of squares to write 26^2 - 24^2 as (26 + 24)(26 - 24).', 'The first factor is 26 + 24 = {result}.'),
('Square both sides of sqrt(3x - 5) = 2 to obtain 3x - 5 = 2^2.', 'The squared right-hand side is 2^2 = {result}.'),
('Use a common denominator: x/2 + x/3 = (3x + 2x)/6. The numerator is (3 + 2)x.', 'The numerator coefficient is 3 + 2 = {result}.'),
('The interior angles of a convex quadrilateral sum to 360 degrees. Each of the two right angles measures 90 degrees.', 'The sum of the two right angles is 90 + 90 = {result} degrees.'),
('For x != 5, multiply both sides by 3(x - 5) to obtain 2(x - 5) = 4 * 3.', 'The right-hand side is 4 * 3 = {result}.'),
('Use denominator 15 to write the total eaten as 3/15 + 10/15 = (3 + 10)/15.', 'The combined numerator is 3 + 10 = {result}.'),
('The sixth term is halfway between the fourth and eighth terms, so it equals (200 + 500)/2.', 'The numerator of this average is 200 + 500 = {result}.'),
('Factor the product under the square root: 10 * 15 * 24 = (2 * 5)(3 * 5)(2^3 * 3) = 2^4 * 3^2 * 5^2.', 'The power of 2 in this product is 2^4 = {result}.'),
('Let S be the total number of students. From (2/3)S = 834, we obtain S = (3 * 834)/2.', 'The numerator is 3 * 834 = {result}.'),
('Let d and n be the numbers of dimes and nickels. The equations are d + n = 11 and 10d + 5n = 75.', 'The constant from expanding 2(11 - n) is 2 * 11 = {result}.'),
('Substitute x = 4 into the line equation to obtain 3 * 4 + 2b = 12.', 'The substituted x term is 3 * 4 = {result}.'),
('Since 441 = 21^2 and 361 = 19^2, the expression is the perfect square (21 + 19)^2.', 'The sum inside the square is 21 + 19 = {result}.'),
('The sum of four numbers is their mean multiplied by 4.', 'The required sum is 4 * 9 = {result}.'),
('The midpoint is ((-5 + 3)/2, (5 + 7)/2). First calculate the numerator of its x coordinate.', 'The x-coordinate numerator is -5 + 3 = {result}.'),
('There are 12 inches in one foot. Convert the 2-foot length to inches before forming the fraction.', 'The length in inches is 2 * 12 = {result}.'),
('The radical conjugate is 5 - sqrt(3). The product is (5 + sqrt(3))(5 - sqrt(3)) = 5^2 - 3.', 'The square in this difference is 5^2 = {result}.'),
('Add 10 to both sides to obtain 10^x = 9990 + 10.', 'The right-hand side is 9990 + 10 = {result}.'),
('The sequence starts at 1 and increases by 2. Its 2003rd term is 1 + 2002 * 2.', 'The increase from the first term is 2002 * 2 = {result}.'),
('Calculate the full price of Susan\'s four tickets before applying her discount.', 'The full price is 4 * 20 = {result} dollars.'),
('Evaluate the inner function first: f(5) = 2 * 5 - 3.', 'The product in this expression is 2 * 5 = {result}.'),
('The input fraction 10/21 is simplified. Substituting into the operation gives 7 * 10 * (21/30).', 'The first product is 7 * 10 = {result}.'),
('To combine the fractions, use the product of their denominators as a common denominator.', 'This common denominator is 4 * 5 = {result}.'),
('Let x be the nonzero number. The equation is 3 + 1/x = 7/x. Subtracting 1/x gives 3 = (7 - 1)/x.', 'The numerator on the right is 7 - 1 = {result}.'),
('Group like terms to write the expression as (19 - 4)x + (1 - 81).', 'The coefficient of x is 19 - 4 = {result}.'),
('Substitute x = -2 to obtain f(-2) = 5(-2)^2 + 3(-2) + 4.', 'The square in this expression is (-2)^2 = {result}.'),
('Substitute a = 8 and evaluate a^2 before taking the inner cube root.', 'The value of a^2 is 8^2 = {result}.'),
('Expand and collect terms to obtain 5x + 2 = 17. Subtract 2 from both sides.', 'The right-hand side after subtraction is 17 - 2 = {result}.'),
('Divisibility by 6 requires an even last digit and a digit sum divisible by 3. Sum the fixed digits before adding N.', 'The sum of the fixed digits is 2 + 1 + 4 + 2 + 0 = {result}.'),
('Multiply the numerical coefficients in the numerator before simplifying the powers of r.', 'The numerator coefficient is 10 * 4 = {result}.'),
('Let p and e be the prices in cents. The equations are 3p + e = 124 and 5p + e = 182. Subtract the first from the second.', 'The difference in total costs is 182 - 124 = {result} cents.'),
('Multiply both the numerator and the denominator of 9/2 by 5 to obtain a denominator of 10.', 'The new numerator is 9 * 5 = {result}.'),
('Expand both products before subtracting. In (u - 3)(u + 6), the constant term comes from (-3) * 6.', 'This constant term is (-3) * 6 = {result}.'),
('The number of girls must be a multiple of 13 and cannot exceed 35. Calculate twice 13 as a candidate.', 'This candidate number of girls is 2 * 13 = {result}.'),
('Substitute a = 5 and b = 1 into the definition to obtain 9 * 5 + 2 * 1 - 5 * 1 + 5.', 'The first product is 9 * 5 = {result}.'),
('Fair representation uses each grade\'s share of the total enrollment. First add the two grade enrollments.', 'The total enrollment is 520 + 650 = {result}.'),
('The class mean is the total score divided by 30. First calculate the total score for the 20 students who scored 80.', 'This group contributed 20 * 80 = {result} points.'),
('Martha walks along two adjacent sides of the rectangular field. Her route length is the sum of the width and length.', 'The length of Martha\'s route is 300 + 400 = {result} feet.'),
('Let t, s, and g denote the respective weights. The equations are 10t = 3s + g and 2t + g = s.', 'The coefficient of t after combining terms is 10 + 2 = {result}.'),
('The 12 meals serve 18 people, so each meal serves 18/12 = 3/2 people. The meals needed for 12 people equal 12/(3/2) = (2 * 12)/3.', 'The numerator is 2 * 12 = {result}.'),
('Change division to multiplication by the reciprocal: (1/5) * (8/7) * (20/12). Cancel common factors to obtain (1 * 2 * 4)/(7 * 3).', 'The denominator after cancellation is 7 * 3 = {result}.'),
('Expand the first product 4(3r^3 + 5r - 6). Its linear term comes from multiplying 4 by 5r.', 'The coefficient of this linear term is 4 * 5 = {result}.'),
]

def arithmetic(expression):
    """Evaluate only the integer arithmetic used by the construction metadata."""
    operations = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Pow: operator.pow}
    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) is int:
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -visit(node.operand)
        if isinstance(node, ast.BinOp) and type(node.op) in operations:
            return operations[type(node.op)](visit(node.left), visit(node.right))
        raise ValueError('Unsupported arithmetic expression')
    return visit(ast.parse(expression, mode='eval').body)

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--check-inputs', action='store_true', help='Validate cached-tokenizer lengths and step boundaries; never load model weights')
    parser.add_argument('--overwrite', action='store_true', help='Replace generated construction artifacts')
    args = parser.parse_args()
    root, data = args.root, args.root / 'data'
    sources = read_jsonl(data / 'formal_50_source.jsonl')
    selections = read_jsonl(data / 'formal_50_selection.jsonl')
    dev_ids = {r['problem_id'] for r in read_jsonl(data / 'dev_5.jsonl')}
    assert len(sources) == len(selections) == len(CONSTRUCTIONS) == 50
    rows, variants = [], []
    for source, selection, (prefix, template) in zip(sources, selections, CONSTRUCTIONS):
        uid = source['unique_id']
        assert uid == selection['unique_id'] and uid not in dev_ids
        value = arithmetic(selection['target_expression_python'])
        assert value == selection['correct_result'] and value + 1 == selection['incorrect_result']
        assert template.count('{result}') == 1
        prefixes = [prefix]
        if selection['formal_id'] == 'formal_019':
            prefixes.append('Divide the value equation by 5 to get 2d + n = 15. Substitute d = 11 - n to obtain 2(11 - n) + n = 15.')
        if selection['formal_id'] == 'formal_047':
            prefixes.append('Add the equations and cancel g to obtain 10t + 2t = 3s + s. The left side is (10 + 2)t.')
        correct, incorrect = template.format(result=value), template.format(result=value + 1)
        row = {'problem_id': uid, 'formal_id': selection['formal_id'], 'split': 'formal', 'source_dataset': 'HuggingFaceH4/MATH-500', 'source_split': 'test', 'source_provenance': 'User-provided 500-row export; upstream revision not supplied', 'subject': source['subject'], 'level': source['level'], 'problem': source['problem'], 'source_solution': source['solution'], 'answer': source['answer'], 'prefix_steps': prefixes, 'correct_step': correct, 'incorrect_step': incorrect, 'edit_rule': 'integer_result_plus_one', 'target_expression_python': selection['target_expression_python'], 'correct_result': value, 'incorrect_result': value + 1, 'edit_reason': f'The correct result is {value}; change only this claimed result to {value + 1}.', 'adaptation_note': 'English rewrite with explicit intermediate arithmetic; truncated immediately after the target. ' + selection['selection_rationale'], 'review_status': 'assistant_reviewed', 'user_review_status': 'not_yet_reviewed'}
        rows.append(row)
        assert all(s.strip() and '\n' not in s and '\r' not in s for s in prefixes + [correct, incorrect])
        for label, original in [('C', correct), ('E', incorrect)]:
            for tone, wording in TEMPLATES.items():
                stem = original if tone == 'B' else original[0].lower() + original[1:]
                steps = prefixes + [wording.format(step=stem)]
                v = {'problem_id': uid, 'formal_id': row['formal_id'], 'split': 'formal', 'condition': f'{label}-{tone}', 'correct': label == 'C', 'tone': tone, 'problem': source['problem'], 'steps': steps, 'target_step_index': len(steps)-1, 'response': '\n'.join(steps)}
                assert v['steps'][:-1] == prefixes and '\\boxed' not in v['response']
                variants.append(v)
    assert len({r['problem_id'] for r in rows}) == 50
    assert len({(v['problem_id'], v['condition']) for v in variants}) == 300
    token_report = {'status': 'not_run'}
    if args.check_inputs:
        from huggingface_hub import snapshot_download
        from transformers import AutoTokenizer
        sys.path.insert(0, str(root / 'skywork-o1-prm-inference'))
        from model_utils.io_utils import prepare_input
        snapshot = snapshot_download(MODEL_ID, revision=REVISION, local_files_only=True)
        tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True)
        lengths = []
        for v in variants:
            ids, steps, flags = prepare_input(v['problem'], v['response'], tokenizer, step_token='\n')
            positions = [i for i, flag in enumerate(flags) if flag]
            assert len(steps) == len(positions) == len(v['steps'])
            assert positions[-1] == len(ids)-1 and len(ids) <= 512
            lengths.append(len(ids))
        token_report = {'status': 'passed', 'checked_inputs': 300, 'min_tokens': min(lengths), 'max_tokens': max(lengths), 'limit': 512, 'truncation': False, 'model_snapshot': REVISION}
    payloads = {'formal_50.jsonl': ''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows), 'formal_50_variants.jsonl': ''.join(json.dumps(v, ensure_ascii=False)+'\n' for v in variants)}
    manifest = {'purpose': 'Constructed formal evaluation inputs; no model scoring performed', 'questions': 50, 'inputs': 300, 'conditions': ['C-B','C-N','C-A','E-B','E-N','E-A'], 'templates': TEMPLATES, 'edit_rule': 'integer_result_plus_one', 'unit_of_analysis': 'question; six conditions are paired within each question', 'source_sha256': hashlib.sha256((data/'formal_50_source.jsonl').read_bytes()).hexdigest(), 'selection_sha256': hashlib.sha256((data/'formal_50_selection.jsonl').read_bytes()).hexdigest(), 'artifact_sha256': {k: hashlib.sha256(v.encode()).hexdigest() for k,v in payloads.items()}, 'checks': {'distinct_questions': 50, 'development_overlap': 0, 'arithmetic_targets_verified': 50, 'single_result_replacement': 50, 'shared_prefix_and_final_target': 300, 'tokenizer': token_report}, 'review_status': 'assistant_reviewed; not user reviewed', 'limitations': ['Purposive sample; not representative of all MATH-500', 'One fixed confident phrase and one fixed neutral phrase; phrase and confidence effects are not fully separable', 'Always adding one studies one specific arithmetic corruption, not all error types', 'Metadata includes reference answers; pass only problem and response to the model']}
    payloads['formal_50_construction_manifest.json'] = json.dumps(manifest, indent=2)+'\n'
    review = ['# Constructed formal evaluation set', '', 'All 50 questions have six paired wording conditions. Source text is preserved in formal_50.jsonl; the reference solution and answer are metadata only. Model inputs are in formal_50_variants.jsonl.', '', 'Status: reviewed by the assistant, not yet reviewed by the user. No model scores were used or generated. Every wrong target changes only the claimed integer result by +1. Prefixes end before the target result is derived, and no continuation is included.', '', '## Wording templates', '', '- B: {step}', '- N: For this step, {step}', '- A: Without any doubt, {step}', '', 'For N and A, only the first letter of the target sentence is lowercased. Prefixes stay identical.', '']
    for r in rows:
        review.extend([f"## {r['formal_id']} — {r['problem_id']}", '', '**Problem**', '', r['problem'], '', '**Shared prefix**', ''])
        review.extend(f'{i}. {s}' for i,s in enumerate(r['prefix_steps'],1))
        review.extend(['', '**Correct target**', '', r['correct_step'], '', '**Incorrect target**', '', r['incorrect_step'], '', '**Adaptation**', '', r['adaptation_note'], ''])
    payloads['formal_50_constructed_review.md'] = '\n'.join(review)
    for name, content in payloads.items():
        path = data / name
        if path.exists() and path.read_text() != content and not args.overwrite:
            raise FileExistsError(f'Refusing to overwrite changed artifact: {path}')
    for name, content in payloads.items():
        (data/name).write_text(content, encoding='utf-8')
    assert read_jsonl(data/'formal_50.jsonl') == rows
    assert read_jsonl(data/'formal_50_variants.jsonl') == variants
    print(json.dumps(manifest['checks'], indent=2))
    print('Saved 50 constructed questions and 300 variants. No model weights were loaded.')

if __name__ == '__main__':
    main()
