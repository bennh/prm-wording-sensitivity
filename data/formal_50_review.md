# Formal 50 question selection

This is a purposive suitability sample, not a random or representative MATH-500 sample. No PRM scores were used for selection. The five development questions are excluded.

The source JSONL preserves all original fields. The proposed targets below are construction aids, not reviewed model inputs. Unpack compressed arithmetic where necessary; keep the prefix correct, omit the target result from the prefix, and stop immediately after the target step. Replace only the claimed result n with n+1 in the error condition. Never include the source answer or later solution in the model input.

| ID | Source ID | Subject | Level | Correct intermediate calculation | Wrong result |
| --- | --- | --- | --- | --- | --- |
| formal_001 | test/algebra/2584.json | Algebra | 3 | `3 * (-2) = -6` | -5 |
| formal_002 | test/algebra/2036.json | Algebra | 3 | `2 - (-4) = 6` | 7 |
| formal_003 | test/algebra/1098.json | Algebra | 3 | `2 * 6 = 12` | 13 |
| formal_004 | test/prealgebra/1840.json | Prealgebra | 2 | `20 * 2 = 40` | 41 |
| formal_005 | test/prealgebra/572.json | Prealgebra | 2 | `3 * 5 = 15` | 16 |
| formal_006 | test/algebra/722.json | Algebra | 1 | `99 + 1 = 100` | 101 |
| formal_007 | test/prealgebra/1247.json | Prealgebra | 2 | `50 - 6 = 44` | 45 |
| formal_008 | test/prealgebra/307.json | Prealgebra | 1 | `5 * 6 = 30` | 31 |
| formal_009 | test/prealgebra/1924.json | Prealgebra | 2 | `4 - 2 = 2` | 3 |
| formal_010 | test/algebra/2593.json | Algebra | 2 | `26 + 24 = 50` | 51 |
| formal_011 | test/algebra/2251.json | Algebra | 2 | `2 ** 2 = 4` | 5 |
| formal_012 | test/prealgebra/505.json | Prealgebra | 2 | `3 + 2 = 5` | 6 |
| formal_013 | test/prealgebra/1807.json | Prealgebra | 3 | `90 + 90 = 180` | 181 |
| formal_014 | test/algebra/988.json | Algebra | 1 | `4 * 3 = 12` | 13 |
| formal_015 | test/prealgebra/1272.json | Prealgebra | 1 | `3 + 10 = 13` | 14 |
| formal_016 | test/algebra/841.json | Algebra | 1 | `200 + 500 = 700` | 701 |
| formal_017 | test/prealgebra/1113.json | Prealgebra | 2 | `2 ** 4 = 16` | 17 |
| formal_018 | test/prealgebra/1922.json | Prealgebra | 2 | `3 * 834 = 2502` | 2503 |
| formal_019 | test/algebra/2199.json | Algebra | 1 | `2 * 11 = 22` | 23 |
| formal_020 | test/algebra/109.json | Algebra | 2 | `3 * 4 = 12` | 13 |
| formal_021 | test/algebra/1937.json | Algebra | 1 | `21 + 19 = 40` | 41 |
| formal_022 | test/prealgebra/1907.json | Prealgebra | 2 | `4 * 9 = 36` | 37 |
| formal_023 | test/algebra/864.json | Algebra | 2 | `-5 + 3 = -2` | -1 |
| formal_024 | test/prealgebra/1458.json | Prealgebra | 3 | `2 * 12 = 24` | 25 |
| formal_025 | test/intermediate_algebra/149.json | Intermediate Algebra | 1 | `5 ** 2 = 25` | 26 |
| formal_026 | test/prealgebra/1317.json | Prealgebra | 1 | `9990 + 10 = 10000` | 10001 |
| formal_027 | test/algebra/524.json | Algebra | 2 | `2002 * 2 = 4004` | 4005 |
| formal_028 | test/algebra/2551.json | Algebra | 1 | `4 * 20 = 80` | 81 |
| formal_029 | test/algebra/346.json | Algebra | 2 | `2 * 5 = 10` | 11 |
| formal_030 | test/algebra/1842.json | Algebra | 2 | `7 * 10 = 70` | 71 |
| formal_031 | test/algebra/2735.json | Algebra | 2 | `4 * 5 = 20` | 21 |
| formal_032 | test/algebra/251.json | Algebra | 2 | `7 - 1 = 6` | 7 |
| formal_033 | test/prealgebra/1298.json | Prealgebra | 2 | `19 - 4 = 15` | 16 |
| formal_034 | test/algebra/849.json | Algebra | 1 | `(-2) ** 2 = 4` | 5 |
| formal_035 | test/algebra/114.json | Algebra | 1 | `8 ** 2 = 64` | 65 |
| formal_036 | test/prealgebra/977.json | Prealgebra | 2 | `17 - 2 = 15` | 16 |
| formal_037 | test/prealgebra/65.json | Prealgebra | 2 | `2 + 1 + 4 + 2 + 0 = 9` | 10 |
| formal_038 | test/algebra/2680.json | Algebra | 2 | `10 * 4 = 40` | 41 |
| formal_039 | test/algebra/2743.json | Algebra | 2 | `182 - 124 = 58` | 59 |
| formal_040 | test/prealgebra/2019.json | Prealgebra | 2 | `9 * 5 = 45` | 46 |
| formal_041 | test/algebra/2080.json | Algebra | 3 | `(-3) * 6 = -18` | -17 |
| formal_042 | test/prealgebra/996.json | Prealgebra | 1 | `2 * 13 = 26` | 27 |
| formal_043 | test/algebra/2789.json | Algebra | 1 | `9 * 5 = 45` | 46 |
| formal_044 | test/algebra/2476.json | Algebra | 2 | `520 + 650 = 1170` | 1171 |
| formal_045 | test/prealgebra/846.json | Prealgebra | 3 | `20 * 80 = 1600` | 1601 |
| formal_046 | test/prealgebra/1252.json | Prealgebra | 2 | `300 + 400 = 700` | 701 |
| formal_047 | test/algebra/1035.json | Algebra | 3 | `10 + 2 = 12` | 13 |
| formal_048 | test/algebra/1787.json | Algebra | 2 | `2 * 12 = 24` | 25 |
| formal_049 | test/prealgebra/1995.json | Prealgebra | 3 | `7 * 3 = 21` | 22 |
| formal_050 | test/algebra/1547.json | Algebra | 3 | `4 * 5 = 20` | 21 |

## Construction notes

- formal_001: Evaluate the numerator of f(-2); then evaluate and add the three function values.
- formal_002: Compute the horizontal coordinate difference before applying the distance formula.
- formal_003: Compute the imaginary coefficient when distributing 6, before combining imaginary terms.
- formal_004: Compute cupcake revenue before adding other revenue and subtracting costs.
- formal_005: Scale the numerator while converting the denominator to 100; then write the decimal.
- formal_006: Evaluate the parentheses in 99(99+1)+1 before multiplying and adding.
- formal_007: Count students in at least one club before finding the overlap.
- formal_008: Count shirt-pants combinations before multiplying by the number of hats.
- formal_009: Combine constant terms before writing the complete simplified expression.
- formal_010: Evaluate the sum in the difference-of-squares factorization before multiplying factors.
- formal_011: Square the right-hand side before isolating x.
- formal_012: Combine numerator coefficients over denominator 6 before solving for x.
- formal_013: Add the two right angles before finding the remaining angles.
- formal_014: Evaluate the right side after cross multiplication before solving the linear equation.
- formal_015: Add converted numerators before writing the resulting fraction.
- formal_016: Compute the numerator of the average before dividing by 2.
- formal_017: Evaluate the power of 2 inside the prime-factorized radicand before taking the square root.
- formal_018: Unpack (3/2)*834 by multiplying first, then dividing by 2.
- formal_019: Expand 2(11-n)+n=15 before collecting terms and solving for n.
- formal_020: Evaluate the substituted x term before solving for the other coordinate.
- formal_021: Evaluate the sum in the perfect square before squaring.
- formal_022: Recover the total from the mean before subtracting the known values.
- formal_023: Add x coordinates before dividing by 2 and forming the ordered pair.
- formal_024: Convert feet to inches before forming and simplifying the fraction.
- formal_025: Evaluate the square in the conjugate product before subtracting 3.
- formal_026: Isolate the power of 10 before determining its exponent.
- formal_027: Compute the offset in 1+2002*2 before adding the first term.
- formal_028: Compute the full price of Susan's tickets before applying discounts and comparing payments.
- formal_029: Evaluate the multiplication in f(5) before continuing the function composition.
- formal_030: Evaluate the first product in the defined operation before multiplying by 21/30.
- formal_031: Compute a common denominator before expanding and subtracting the numerators.
- formal_032: Subtract reciprocal coefficients before solving for the unknown number.
- formal_033: Combine x coefficients before writing the full simplified expression.
- formal_034: Evaluate the square after substitution before multiplying by 5 and adding other terms.
- formal_035: Evaluate a squared before taking the inner cube root and continuing.
- formal_036: Isolate 5x before solving for x and evaluating the requested expression.
- formal_037: Sum the fixed digits before applying divisibility conditions to N.
- formal_038: Multiply numerator coefficients before dividing coefficients and simplifying powers.
- formal_039: Subtract the total costs in cents before dividing by the difference in pencil counts.
- formal_040: Scale the numerator while converting the denominator to 10; then write the decimal.
- formal_041: Compute the constant term in the second product before subtracting the two polynomials.
- formal_042: Construct a candidate multiple for the number of girls before checking the majority and counting boys.
- formal_043: Evaluate the first product after substitution into the defined operation.
- formal_044: Compute total enrollment before forming the grade proportion and allocating representatives.
- formal_045: Compute the first group's total marks before adding the other groups and averaging.
- formal_046: Compute the route along two sides before comparing with the diagonal route.
- formal_047: Combine treek coefficients after eliminating g before solving for the weight ratio.
- formal_048: Unpack (2/3)*12 by multiplying first, then dividing by 3.
- formal_049: Compute the denominator after cancellation before writing the final fraction.
- formal_050: Compute the linear coefficient in the first expanded product before combining like terms.
