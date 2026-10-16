# The Maths Behind Fractal Maker

This guide explains the mathematics behind every picture the app draws, and
shows where each idea lives in the code. It starts from scratch: if you know
what a square and a square root are, you can follow it. Each section builds on
the one before, so reading in order works best.

Small Python snippets are included so you can check every claim yourself:
paste them into `python3`.

## Contents

1. [Complex numbers](#1-complex-numbers)
2. [Iteration and orbits](#2-iteration-and-orbits)
3. [The Mandelbrot set](#3-the-mandelbrot-set)
4. [Why "escaped past 2" means "gone forever"](#4-why-escaped-past-2-means-gone-forever)
5. [The iteration limit, and a surprise appearance of π](#5-the-iteration-limit-and-a-surprise-appearance-of-π)
6. [Smooth colouring](#6-smooth-colouring)
7. [From numbers to colours](#7-from-numbers-to-colours)
8. [Julia sets](#8-julia-sets)
9. [Anatomy of the Mandelbrot set](#9-anatomy-of-the-mandelbrot-set)
10. [The geometry of the screen: pixels, views and zooming](#10-the-geometry-of-the-screen-pixels-views-and-zooming)
11. [How deep can you zoom? Floating-point limits](#11-how-deep-can-you-zoom-floating-point-limits)
12. [Beyond z²: Multibrot sets](#12-beyond-z²-multibrot-sets)
13. [How the code is organised (briefly)](#13-how-the-code-is-organised-briefly)
14. [Exercises](#14-exercises)
15. [Glossary](#15-glossary)

---

## 1. Complex numbers

### 1.1 Numbers as points

A **complex number** has two parts, written

```
z = x + y·i
```

where `x` is the **real part**, `y` is the **imaginary part**, and `i` is a
special number with the property

```
i² = −1
```

No ordinary number squares to −1, which is why `i` is called "imaginary". But
you don't have to find it mysterious. Just treat `x + y·i` as the **point
`(x, y)`** on a flat plane. This plane is called the **complex plane**: the
horizontal axis holds the real part, and the vertical axis the imaginary part.

```
          imaginary
              ↑
         2i   ┼          • 3 + 2i
              │
          i   ┼
              │
   ──┼────┼───┼───┼───┼───┼──→ real
    −2   −1   0   1   2   3
              │
         −i   ┼     • 1 − i
```

**Every pixel on the screen is one complex number.** That's the link between
this maths and the picture.

### 1.2 Adding

Add the real parts and the imaginary parts separately:

```
(1 + 2i) + (3 − i) = 4 + i
```

Geometrically, that's adding arrows: walk to the first point, then walk the
second arrow from there.

### 1.3 Multiplying

Multiply out the brackets like normal algebra, then replace `i²` with `−1`:

```
(a + b·i)(c + d·i) = ac + ad·i + bc·i + bd·i²
                   = (ac − bd) + (ad + bc)·i
```

The important special case is **squaring**:

```
(x + y·i)² = (x² − y²) + (2xy)·i
```

Example: `(1 + 2i)² = (1 − 4) + (2·1·2)i = −3 + 4i`.

### 1.4 Size and angle (polar form)

The **modulus** `|z|` is the distance from the point to the centre `0`. By
Pythagoras:

```
|x + y·i| = √(x² + y²)
```

The **argument** `θ` is the angle the point makes with the positive real
axis. Any complex number can be described by its size `r = |z|` and its angle
`θ` instead of `x` and `y`. This is called **polar form**.

Here is the key fact about multiplication:

> **When you multiply two complex numbers, their sizes multiply and their
> angles add.**

So **squaring** a number squares its size and **doubles** its angle:

| `z` | size | angle | `z²` | size | angle |
|---|---|---|---|---|---|
| `1 + i` | √2 ≈ 1.41 | 45° | `2i` | 2 | 90° |
| `0.5i` | 0.5 | 90° | `−0.25` | 0.25 | 180° |
| `−2` | 2 | 180° | `4` | 4 | 360° = 0° |

This is the single most useful fact in this guide:

- Points with `|z| < 1` get **smaller** when squared (0.5 → 0.25).
- Points with `|z| > 1` get **bigger** when squared (2 → 4).
- Squaring also spins the point around the centre (angle doubled), which is
  where all the swirls come from.

### 1.5 In Python

Python has complex numbers built in. It writes `i` as `j`:

```python
>>> z = 1 + 2j
>>> z * z
(-3+4j)
>>> abs(z)          # the modulus |z|
2.23606797749979
>>> z.real, z.imag
(1.0, 2.0)
```

---

## 2. Iteration and orbits

To **iterate** a rule means to apply it over and over, feeding each answer
back in. Every fractal in this app iterates one rule:

```
z  →  z² + c
```

where `c` is a fixed complex number. Start with some `z₀`, then

```
z₁ = z₀² + c
z₂ = z₁² + c
z₃ = z₂² + c
…
```

The list `z₀, z₁, z₂, …` is called the **orbit** of `z₀`. Let's compute some
orbits by hand, always starting from `z₀ = 0`.

**c = 0:** `0, 0, 0, …`. The orbit stays put. `0` is a **fixed point**.

**c = 1:**

| n | zₙ |
|---|---|
| 0 | 0 |
| 1 | 0² + 1 = 1 |
| 2 | 1² + 1 = 2 |
| 3 | 2² + 1 = 5 |
| 4 | 5² + 1 = 26 |
| 5 | 26² + 1 = 677 |

The orbit **escapes**: it runs off to infinity.

**c = −1:** `0, −1, 0, −1, …`. The orbit bounces between two values forever.
This is a **cycle of period 2**.

**c = i:** (using `i² = −1`)

| n | zₙ |
|---|---|
| 0 | 0 |
| 1 | 0 + i = i |
| 2 | i² + i = −1 + i |
| 3 | (−1 + i)² + i = (1 − 2i − 1) + i = −i |
| 4 | (−i)² + i = −1 + i |
| 5 | −i |

After a couple of steps it bounces between `−1 + i` and `−i` forever. It's
**bounded** (it stays within a fixed distance of 0) but never settles down.

**c = −2:** `0, −2, 2, 2, 2, …`. It lands on the fixed point `2` and stays
there. Bounded, but only just: we'll see that −2 is the very tip of the
Mandelbrot set.

So orbits do one of two things:

- they are **bounded**: settling down, cycling, or wandering, but staying
  near 0, or
- they **escape** to infinity.

Telling those two apart, for millions of starting points, is what this app
does.

---

## 3. The Mandelbrot set

> **Definition.** The **Mandelbrot set** `M` is the set of complex numbers `c`
> for which the orbit of `0` under `z → z² + c` stays bounded.

From section 2: `0`, `−1`, `i` and `−2` are in `M`, and `1` is not.

To draw `M`:

1. Treat every pixel as a value of `c` (its position on the complex plane).
2. Iterate `z → z² + c` starting from `z = 0`.
3. If the orbit stays bounded, colour the pixel **black**.
4. If it escapes, colour it by **how many steps** it took. Points that escape
   fast are far from the set; points that take ages are very close to its
   edge.

This is called the **escape-time algorithm**. In the code it is the function
`escape_count` in `fractals/mandelbrot.py`:

```python
def escape_count(z, c, max_iter):
    for n in range(max_iter):
        z = z * z + c
        mag_sq = z.real * z.real + z.imag * z.imag
        if mag_sq > ESCAPE_RADIUS_SQ:
            return n + 1 - math.log(math.log(math.sqrt(mag_sq))) / LOG2
    return math.nan
```

and `mandelbrot_counts` calls it with `z = 0` for every pixel's `c`.

Two questions remain, and the next two sections answer them:

- How can we know an orbit *will* escape, without iterating forever?
  (Section 4.)
- How can we know an orbit *won't* escape? We can't, which is why there's an
  iteration limit. (Section 5.)

---

## 4. Why "escaped past 2" means "gone forever"

### 4.1 The theorem

> **Escape theorem.** If at some step `|zₙ| > 2` and `|zₙ| ≥ |c|`, then the
> orbit escapes to infinity.

We only need one tool, the **reverse triangle inequality**: for any complex
numbers `a` and `b`,

```
|a + b| ≥ |a| − |b|
```

(The direct path between two points is never longer than a detour, rearranged.)

**Proof.** Write `r = |zₙ|`, so `r > 2` and `r ≥ |c|`. Then

```
|zₙ₊₁| = |zₙ² + c|
       ≥ |zₙ²| − |c|        (reverse triangle inequality)
       = r² − |c|
       ≥ r² − r             (because |c| ≤ r)
       = r · (r − 1)
```

Since `r > 2`, the factor `r − 1` is bigger than 1. Write it as `1 + ε` with
`ε = r − 2 > 0`. So

```
|zₙ₊₁| ≥ (1 + ε) · |zₙ|
```

Each step multiplies the size by at least `1 + ε`. The new value is still
bigger than 2 and still at least `|c|`, so the same argument applies to the
next step, and the next. And `ε` can only grow, because the size keeps
growing. After `k` more steps, `|zₙ₊ₖ| ≥ (1 + ε)ᵏ · |zₙ|`, which goes to
infinity. ∎

### 4.2 Getting rid of the "`|zₙ| ≥ |c|`" condition

- **If `|c| > 2`:** the first step gives `z₁ = c`, so `|z₁| = |c| > 2` and
  `|z₁| ≥ |c|`. By the theorem, it escapes. So **every point of the
  Mandelbrot set lies within distance 2 of the centre**. That's why the
  default view is only about 3.5 units wide.
- **If `|c| ≤ 2`:** then any `|zₙ| > 2` automatically satisfies `|zₙ| ≥ |c|`.

Either way, the rule is simple: **as soon as `|z| > 2`, the orbit has
escaped.** The number 2 is called the **escape radius** (or *bailout*).

### 4.3 Two small tricks in the code

**Comparing squares.** `|z| > R` is the same as `x² + y² > R²`. Comparing the
squared size avoids a square root on every step, which saves time over
billions of steps. So the code computes

```python
mag_sq = z.real * z.real + z.imag * z.imag
if mag_sq > ESCAPE_RADIUS_SQ:
```

**Using 256 instead of 2.** The code uses `ESCAPE_RADIUS_SQ = 256.0 ** 2`.
Any radius of 2 or more gives the same yes/no answer: once past 2, the orbit
will pass 256 a few steps later anyway. The larger radius makes the smooth
colouring in section 6 more accurate.

---

## 5. The iteration limit, and a surprise appearance of π

### 5.1 Why we need a limit

Section 4 tells us when an orbit has *definitely* escaped. But for points in
the set the orbit never escapes, and no finite amount of checking proves it.
So the code gives up after `max_iter` steps (the **"Max iterations"** slider)
and *assumes* the point is inside. Python's `math.nan` ("not a number") marks
those pixels, and they're drawn black.

That's an approximation, and it can be wrong: a point that would escape on
step 301 is drawn black when `max_iter = 300`.

### 5.2 Points near the edge escape slowly

How many steps does escaping take? It depends on how close `c` is to the edge
of the set. The real number `1/4` is on the edge (section 9). Try points just
to the right of it:

```python
def steps(c, limit=100000):
    z = 0
    for n in range(1, limit):
        z = z * z + c
        if abs(z) > 2:
            return n

for eps in [0.1, 0.01, 0.001, 0.0001]:
    print(eps, steps(0.25 + eps))
```

| c | steps to escape |
|---|---|
| 0.35 | 8 |
| 0.26 | 30 |
| 0.251 | 97 |
| 0.2501 | 312 |

Every time we move 10× closer, it takes about 3× more steps (√10 ≈ 3.16).
That's because the orbit crawls through a narrow "bottleneck" near `z = 1/2`.
The number of steps grows like `1/√ε`.

**This is why deep zooms need more iterations.** Zooming in on the edge means
looking at points ever closer to the set, and their orbits take ever longer to
escape. With too few iterations, slowly escaping points are wrongly painted
black, and fine detail turns into black blobs.

### 5.3 π hiding in the Mandelbrot set

Here's a famous surprise, found by Dave Boll in 1991. The point `c = −3/4` is
where the two biggest parts of the set touch (section 9). Approach it from
above, `c = −0.75 + ε·i`, count the steps to escape, and multiply by `ε`:

```python
for eps in [0.1, 0.01, 0.001, 0.0001]:
    n = steps(complex(-0.75, eps))
    print(eps, n, n * eps)
```

| ε | steps | steps × ε |
|---|---|---|
| 0.01 | 315 | 3.15 |
| 0.001 | 3143 | 3.143 |
| 0.0001 | 31417 | 3.1417 |

The digits of **π = 3.14159…** appear, more accurately the closer you get.
Approaching `c = 1/4` from the right gives π too: steps × √ε → π. (From the
table in 5.2: `97 × √0.001 ≈ 3.07` and `312 × √0.0001 = 3.12`, creeping up on
π as ε shrinks.) Nobody expected π
here. It comes from the same bottleneck behaviour as above.

---

## 6. Smooth colouring

### 6.1 The problem: stripes

If pixels are coloured by the whole number of steps (5, 6, 7, …), every pixel
that escaped on step 6 gets exactly the same colour, and the picture shows
hard-edged stripes. You can see them yourself: in `escape_count`, replace the
smooth `return` line with `return float(n)`.

We want a number that changes **continuously** from pixel to pixel: 6.0,
6.1, 6.2, … instead of jumping from 6 to 7.

### 6.2 The idea: measure how far past the radius `z` got

Two pixels might both escape on step 6, but one might land just past the
radius and the other far past it. The second one was "escaping faster". We
can turn that into a fraction.

Once `|z|` is large, adding `c` hardly matters, so each step approximately
**squares** the size:

```
|zₙ₊₁| ≈ |zₙ|²
```

Take the logarithm of both sides. Logarithms turn powers into multiplication,
since `log(a²) = 2·log(a)`:

```
log|zₙ₊₁| ≈ 2 · log|zₙ|
```

Take `log₂` (log base 2) again. That turns "doubling" into "adding 1", since
`log₂(2a) = 1 + log₂(a)`:

```
log₂(log|zₙ₊₁|) ≈ 1 + log₂(log|zₙ|)
```

So the quantity `log₂(log|zₙ|)` goes up by **exactly 1 per step**, just like
the step counter `n`. Their difference therefore stays (almost) constant along
the orbit:

```
ν = n − log₂(log|zₙ|)
```

This `ν` (the Greek letter *nu*) is the **smooth escape count**. Because it
doesn't depend on *which* step we stop at, it doesn't jump when a pixel
switches from "escaped on step 6" to "escaped on step 7". It changes smoothly
across the whole picture.

You can watch it settle down. For `c = 0.4 + 0.3i`:

| stop at step | n − log₂(log\|zₙ\|) |
|---|---|
| 15 | 14.6305 |
| 16 | 14.6317 |
| 17 | 14.63231 |
| 18 | 14.6323140 |
| 19 | 14.6323140 |

The bigger `|z|` is when we stop, the better the approximation `|zₙ₊₁| ≈ |zₙ|²`
holds (because `c` matters less). **That's why the code uses an escape radius
of 256 instead of 2.**

### 6.3 In the code

```python
return n + 1 - math.log(math.log(math.sqrt(mag_sq))) / LOG2
```

- `math.sqrt(mag_sq)` is `|z|`.
- `math.log(x) / LOG2` is `log₂(x)`. The version of numba used here doesn't
  support `math.log2`, so the code divides by `LOG2 = log(2)` instead.
- `n + 1` is the step number, since the loop counts from 0.

---

## 7. From numbers to colours

The fractal code produces a grid of smooth counts `ν` (or NaN for "inside").
`colors.py` turns each one into a colour. Three bits of maths are involved.

### 7.1 Building the palette: piecewise linear interpolation

A palette is a short list of colour "stops", for example

```python
"Fire": [(0, 0, 0), (128, 0, 0), (255, 80, 0),
         (255, 200, 0), (255, 255, 210), (0, 0, 0)],
```

`build_lut` spreads these stops evenly over 256 positions (0 to 255) and fills
the gaps by drawing straight lines between neighbouring stops, separately for
red, green and blue. This is **piecewise linear interpolation**, done by
`np.interp`. The result is a table of 256 colours called a **lookup table
(LUT)**.

The first and last stops are the same colour, so position 255 blends smoothly
back into position 0 and the palette can loop.

### 7.2 Picking a position: square root and wrap-around

```python
position = (math.sqrt(max(value, 0.0)) * COLOR_DENSITY) % LUT_SIZE
```

- **`√ν`:** counts can range from 1 to thousands. Taking the square root
  squashes large values, so deep zooms (big counts) don't race through the
  palette. For example, `√100 = 10` and `√400 = 20`: four times the count,
  only twice the distance through the colours.
- **`× COLOR_DENSITY`** (24): stretches the result, giving more colour bands.
- **`% LUT_SIZE`:** "modulo 256" wraps around, like a clock. For example,
  `√400 × 24 = 480` and `480 % 256 = 224`. That's why colours cycle as you
  zoom.
- **`max(value, 0.0)`:** right at the edge of the escape radius, the smooth
  formula can give slightly negative numbers, and the square root of a
  negative number isn't defined, so negatives are clamped to 0.

### 7.3 Blending between table entries: linear interpolation ("lerp")

`position` is usually not a whole number, for example 41.3. Rather than
rounding (which would make visible steps), the code mixes the two neighbouring
entries:

```
colour = (1 − t) · table[41] + t · table[42],    t = 0.3
```

so it's 70% of entry 41 and 30% of entry 42. In general, `(1 − t)·a + t·b`
slides from `a` (at `t = 0`) to `b` (at `t = 1`). It's the formula for a point
partway along a straight line, and it's called **linear interpolation**, or
**lerp** for short.

---

## 8. Julia sets

### 8.1 Same formula, swapped roles

Julia sets use the same rule `z → z² + c`, but with the roles of `z` and `c`
swapped:

| | Mandelbrot set | Julia set `J_c` |
|---|---|---|
| `c` | the pixel's position (changes per pixel) | **one fixed number** for the whole picture |
| starting `z` | always `0` | the pixel's position |
| how many sets | one | one for every `c`, so infinitely many |

> **Definition.** For a fixed `c`, the **filled Julia set** `K_c` is the set
> of starting points `z₀` whose orbit under `z → z² + c` stays bounded.

(Strictly speaking, the *Julia set* `J_c` is the **boundary** of `K_c`. The
app draws the filled version: the inside is black and the coloured outside
shows escape times.)

In the code, `julia_counts` in `fractals/julia.py` calls the same
`escape_count`, passing each pixel as `z` and the slider value as `c`.

### 8.2 The big theorem: connected or dust

Julia sets come in exactly two kinds:

- **Connected:** one single piece (you could walk from any point of it to any
  other without leaving it).
- **Dust:** shattered into infinitely many separate points, with no two
  joined. Mathematicians call this a *Cantor set*, or **Fatou dust**.

Which kind you get is decided by one orbit: the orbit of `0`.

> **Fatou–Julia theorem.** The Julia set `J_c` is connected if the orbit of 0
> is bounded, and is dust if the orbit of 0 escapes.

But "the orbit of 0 is bounded" is *exactly* the definition of `c` being in
the Mandelbrot set! So:

> **The Mandelbrot set is a map of all Julia sets:** `c` is in `M` exactly when
> `J_c` is connected.

Why does 0 matter so much? `0` is the **critical point** of `f(z) = z² + c`:
the only point where the derivative `f′(z) = 2z` is zero, where the map folds
the plane over onto itself. The fate of that one special point controls the
shape of the whole Julia set.

**See it in the app:** Shift+click on the Mandelbrot view opens the Julia set
for the `c` you clicked. Click inside the black area and you get a connected
shape. Click outside and you get dust. The further outside you click, the
finer the dust.

### 8.3 The presets, explained

| Preset | `c` | In `M`? | What you see |
|---|---|---|---|
| Douady rabbit | −0.123 + 0.745i | yes | connected. `c` is in a period-3 bulb (section 9), so the orbit of 0 settles into a 3-cycle and the set has 3 "ears" at every junction |
| San Marco | −0.75 | yes (on the edge) | connected; named after the basilica in Venice and its reflection in the water |
| Dragon | 0.36 + 0.1i | yes | connected, with swirling arms |
| Dust (disconnected) | 0.35 + 0.4i | **no** | clearly separate clusters: Fatou dust |
| Dendrite swirl | −0.8 + 0.156i | just outside | looks connected, but the orbit of 0 escapes after about 250 steps, so mathematically it's dust whose gaps are too fine to see |
| Lightning | −0.7269 + 0.1889i | just outside | same: dust, but the gaps are invisible at normal zoom |
| Siegel disk | −0.391 − 0.587i | just outside | near the true "Siegel disk" value ≈ −0.3905 − 0.5868i, where the orbit rotates around a disc-shaped region forever |

You can check the rabbit's 3-cycle yourself:

```python
c, z = complex(-0.123, 0.745), 0
for _ in range(5000):
    z = z * z + c
for _ in range(6):
    z = z * z + c
    print(f"{z:.4f}")
# repeats: -0.6629+0.5617j, 0.0009+0.0003j, -0.1230+0.7450j, ...
```

### 8.4 Symmetry

- **Every Julia set looks the same after a half-turn about the centre** (it
  has 180° rotational symmetry). That's because `(−z)² = z²`, so `z` and `−z`
  have identical futures.
- **The Mandelbrot set is a mirror image of itself across the real axis.**
  Flipping `c` to its mirror image `c̄` (`x + yi → x − yi`) flips every point
  of the orbit too, and mirror images have the same size.

---

## 9. Anatomy of the Mandelbrot set

The Mandelbrot set has recognisable parts, and several of them have exact
formulas.

### 9.1 The main cardioid: orbits that settle down

The big heart-shaped body (a **cardioid**) contains the values of `c` for
which the orbit of 0 settles down to a single **attracting fixed point**.

A fixed point `z*` satisfies `z* = z*² + c`. It is **attracting** (nearby
orbits get pulled in) when the map shrinks distances near it. That happens
when `|f′(z*)| = |2z*| < 1`.

Write `2z* = μ` with `|μ| < 1`. Then `z* = μ/2`, and solving the fixed-point
equation for `c` gives

```
c = z* − z*² = μ/2 − μ²/4
```

As `μ` goes around the circle `μ = e^{iθ}` (size 1, angle θ), `c` traces the
**edge of the cardioid**:

```
c(θ) = e^{iθ}/2 − e^{2iθ}/4
```

| θ | c | where |
|---|---|---|
| 0 | 0.25 | the **cusp** on the right: the edge point from section 5.2 |
| π/2 | 0.25 + 0.5i | top of the cardioid |
| 2π/3 | −0.125 + 0.6495i | where the period-3 bulb (rabbit) attaches |
| π | −0.75 | where the period-2 disc attaches: Boll's π point from section 5.3 |

### 9.2 The period-2 disc

The circle to the left of the cardioid contains the values of `c` for which
the orbit settles into an attracting **2-cycle** (bouncing between two
values, like `c = −1`). Its exact shape is a perfect disc:

```
|c + 1| < 1/4      (centre −1, radius 1/4)
```

*Why:* the two points of the cycle are the roots of `z² + z + c + 1 = 0`
(this comes from solving `f(f(z)) = z` and removing the fixed points). The
cycle is attracting when the product of the derivatives at both points has
size less than 1. That product is `2z₁ · 2z₂ = 4·(z₁z₂) = 4(c + 1)`, because
the product of a quadratic's roots is its constant term. So the condition is
`|4(c + 1)| < 1`.

### 9.3 Bulbs and their periods

Smaller bulbs sprout all around the cardioid. The bulb attached at angle
`θ = 2π·p/q` (in the formula above) contains orbits that settle into a cycle
of **period q**. The bulb at θ = 2π/3 has period 3; that's where the Douady
rabbit lives, and why it has 3 ears. Each bulb has its own smaller bulbs, and
so on forever.

### 9.4 The real line and the antenna

Along the real axis, the Mandelbrot set is exactly the interval **[−2, 1/4]**.
The thin spike running left to −2 is called the **antenna**. Its tip, `c = −2`,
is the point whose orbit `0, −2, 2, 2, …` we computed in section 2.

### 9.5 Mini-Mandelbrots

Zoom into the antenna or the filaments and you'll find small copies of the
whole set, slightly distorted. There are infinitely many of them. This
self-similarity is part of what makes it a **fractal**: a shape with detail
at every scale.

---

## 10. The geometry of the screen: pixels, views and zooming

The app needs to convert between **screen pixels** (whole numbers, with y
pointing *down*) and **points on the complex plane** (decimals, with y
pointing *up*). All of this is linear algebra at the level of straight-line
graphs.

### 10.1 The view

The visible region is stored as `view = (cx, cy, w)`: the centre point and the
width in plane units. The height isn't stored. It follows from the window's
shape so that pictures are never stretched:

```
h = w · H / W          (W, H = window size in pixels)
```

### 10.2 Pixel → point

`pixel_to_point` in `fractals/base.py`:

```
x = (cx − w/2) + (px / W) · w
y = (cy + h/2) − (py / H) · h
```

- `cx − w/2` is the **left edge** of the view. `px / W` is the fraction of the
  way across the screen, from 0 to 1. So `x` is "left edge plus that fraction
  of the width".
- `cy + h/2` is the **top edge**. We *subtract*, because moving down the
  screen means going down the imaginary axis.

`complex_grid` applies the same formula to every pixel at once, using numpy
arrays.

### 10.3 Zoom level

The status bar shows

```
zoom = w_default / w
```

Zooming ×2 halves `w`.

### 10.4 Three kinds of zoom

**Click (`zoom_centered`):** the clicked point `p` becomes the new centre, and
the width is multiplied by a factor `f` (0.5 to zoom in, 2 to zoom out).

**Scroll (`zoom_fixed`):** the point under the cursor should *stay* under the
cursor. Let `p` be that point. Its offset from the centre, `c − p`, is a
distance on screen, and when the zoom factor is `f` every distance shrinks by
`f`. So the new centre is

```
c_new = p + (c − p) · f
```

Check: with `f = 1` nothing moves. With `f = 0` the view collapses onto `p`.

**Box (`zoom_to_box`):** the box must fit inside the new view in *both*
directions. If the box is `bw × bh` pixels on a `W × H` screen, the new width
is

```
w_new = w · max(bw / W, bh / H)
```

The `max` picks whichever direction is the tighter fit.

### 10.5 The instant preview: an affine map

When you zoom, `show_zoom_preview` instantly stretches the old picture to the
new view, before the sharp version is ready. For each new pixel it needs the
old pixel that shows the same point on the plane.

A new pixel `px` shows the point `x = L_new + px · w_new / W`, where `L` is the
left edge. In the old picture, that point was at pixel
`(x − L_old) · W / w_old`. Substituting:

```
old_px = (w_new / w_old) · px  +  (L_new − L_old) · W / w_old
       =        s         · px  +          offset_x
```

The same working with top edges gives `offset_y`. A rule of the form
"multiply by `s`, then add an offset" is called an **affine map**. Pillow's
`Image.transform(…, Image.AFFINE, (s, 0, offset_x, 0, s, offset_y))` applies
it to every pixel.

---

## 11. How deep can you zoom? Floating-point limits

Computers store decimals as **floating-point** numbers. The app uses 64-bit
floats, which keep about **16 significant digits**. More precisely, two
neighbouring floats near `x` are about `x × 2.2 × 10⁻¹⁶` apart. This tiny
number is called **machine epsilon**.

Neighbouring pixels are `w / W` apart on the plane. Once that gap is smaller
than the gap between neighbouring floats, several pixels get rounded to the
**same** number and the picture turns blocky. With `W ≈ 1000` pixels, points
near `|x| ≈ 0.75`, and a starting width of 3.5:

```
maximum zoom ≈ 3.5 / (1000 × 0.75 × 2.2 × 10⁻¹⁶) ≈ 2 × 10¹³
```

So somewhere around **10¹³×** the app hits its limit. Going deeper requires
"arbitrary-precision" arithmetic (numbers with as many digits as you like),
which is much slower. Dedicated deep-zoom programs use clever tricks such as
*perturbation theory* to get around this.

---

## 12. Beyond z²: Multibrot sets

Nothing forces the power to be 2. Iterating

```
z → z^d + c
```

gives the **Multibrot** sets. Everything in this guide carries over with small
changes:

- **Escape radius:** 2 still works. Section 4's proof becomes
  `|z^d + c| ≥ r^d − r = r(r^{d−1} − 1) > r` when `r > 2`.
- **Smooth colouring:** each step now raises the size to the power `d`, so
  replace `log₂` with `log_d`. In the code, that means changing `LOG2` to
  `math.log(d)`.
- **Symmetry:** the set has `d − 1` lobes arranged with rotational symmetry.
  For `d = 3` you get two big mirrored lobes instead of a heart shape.

To try it, change `z = z * z + c` in `escape_count` to `z = z * z * z + c`.
Julia sets change too, because they share the function.

---

## 13. How the code is organised (briefly)

This guide is about the maths. The code itself is commented line by line. Here
is where each idea lives:

| Maths idea | Code | File |
|---|---|---|
| `z → z² + c`, escape radius, smooth count (§3–6) | `escape_count` | `fractals/mandelbrot.py` |
| Mandelbrot: `z₀ = 0`, `c` = pixel (§3) | `mandelbrot_counts`, `Mandelbrot` | `fractals/mandelbrot.py` |
| Julia: `z₀` = pixel, fixed `c` (§8) | `julia_counts`, `Julia` | `fractals/julia.py` |
| Palette interpolation, √, modulo, lerp (§7) | `build_lut`, `colorize`, `_colorize` | `colors.py` |
| Pixel ↔ plane conversion (§10.2) | `pixel_to_point`, `complex_grid` | `fractals/base.py` |
| Zooms and the affine preview (§10.4–10.5) | `zoom_centered`, `zoom_fixed`, `zoom_to_box`, `show_zoom_preview` | `app.py` |

**What happens when you click**, in one paragraph: `app.py` turns the click
into a new `view` (§10). It immediately shows a stretched preview (§10.5),
then sends a "render job" to a background thread so the window never freezes.
That thread calls the fractal's `render()`, which builds a grid of complex
numbers, runs `escape_count` on every pixel, and colours the result. The
finished image is passed back and drawn on the canvas.

**Why it's fast:** the per-pixel loops are compiled to machine code by the
**numba** library (the `@njit` decorator) and spread across all CPU cores
(`prange`). A full-screen picture is about 4 million pixels × hundreds of
iterations, which would take minutes in plain Python and takes a fraction of
a second this way.

**Adding a new fractal:** create a class in `fractals/` following the
`Fractal` contract in `fractals/base.py`, and register it in
`fractals/__init__.py`. The README has a full fractal-tree example.

---

## 14. Exercises

**By hand**

1. Compute the orbit of 0 for `c = −0.5`. Does it settle down? To what? (Hint:
   solve `z = z² − 0.5`.)
2. Compute the first four steps for `c = 2i`. Show it escapes.
3. `c = −1.75` lies in [−2, 1/4], so it's in the set. Iterate it many times
   (with Python) and look at where the orbit ends up. What kind of cycle is
   it? (It lives in a tiny mini-Mandelbrot on the antenna.)
4. Prove that the orbit of 0 for `c = 0.3` escapes. (Hint: show `zₙ` keeps
   growing once it passes 1/2.)

**With Python**

5. Use the `steps` function from section 5.2 to check Boll's π result for
   ε = 10⁻⁵. How close to π do you get?
6. Check the period-2 disc: pick a few `c` with `|c + 1| < 1/4` and confirm the
   orbit of 0 ends up bouncing between two values.
7. Check that `c(θ) = e^{iθ}/2 − e^{2iθ}/4` lands on the edge of the set: for
   `θ = 1`, compare the escape behaviour of `0.99·c(θ)` and `1.01·c(θ)`.
   (Python: `import cmath; cmath.exp(1j)`.)

**In the app**

8. Shift+click several points inside the cardioid, then in the period-2 disc,
   then in the period-3 bulb. Count the "arms" meeting at the junctions of
   each Julia set. What do you notice?
9. Set `max_iter` to 50 and zoom into the edge, then raise it to 2000. Explain
   what changes using section 5.
10. Change the escape radius to 2 (`ESCAPE_RADIUS_SQ = 2.0 ** 2`). The shape
    is identical but the colours get less smooth. Explain why using
    section 6.

---

## 15. Glossary

| Term | Meaning |
|---|---|
| **Affine map** | "Multiply by a number, then add an offset". Used to stretch the preview when zooming. |
| **Argument** | The angle of a complex number, measured from the positive real axis. |
| **Attracting** | A fixed point or cycle that pulls nearby orbits towards it. |
| **Bounded** | Staying within some fixed distance of 0 forever. |
| **Cardioid** | A heart-shaped curve; the main body of the Mandelbrot set. |
| **Complex number** | `x + y·i` with `i² = −1`; a point `(x, y)` on the complex plane. |
| **Complex plane** | The flat surface where each point is a complex number. |
| **Critical point** | Where the derivative is zero. For `z² + c` it is `z = 0`. |
| **Cycle (period q)** | An orbit that repeats every `q` steps. |
| **Escape radius** | Once `|z|` passes it, the orbit is certain to escape. 2 is enough; the code uses 256. |
| **Escape-time algorithm** | Colour each point by how many steps its orbit takes to escape. |
| **Fatou dust** | A Julia set shattered into separate points; happens when `c` is outside `M`. |
| **Filled Julia set `K_c`** | The starting points whose orbits stay bounded, for a fixed `c`. |
| **Fixed point** | A value that the rule maps to itself: `f(z*) = z*`. |
| **Floating point** | How computers store decimals, with about 16 significant digits. |
| **Fractal** | A shape with detail at every scale, often containing copies of itself. |
| **Iteration** | Applying a rule repeatedly, feeding each output back in. |
| **Julia set `J_c`** | The boundary of `K_c`. |
| **Lerp** | Linear interpolation: `(1 − t)·a + t·b`. |
| **LUT** | Lookup table: precomputed values (here, 256 colours). |
| **Machine epsilon** | The relative gap between neighbouring floats, ≈ 2.2 × 10⁻¹⁶. |
| **Mandelbrot set `M`** | The `c` values for which the orbit of 0 stays bounded. |
| **Modulus `\|z\|`** | The distance from `z` to 0: `√(x² + y²)`. |
| **Multibrot** | The Mandelbrot-style set for `z → z^d + c`. |
| **NaN** | "Not a number"; the code uses it to mean "inside the set". |
| **Orbit** | The sequence `z₀, z₁, z₂, …` produced by iterating. |
| **Smooth escape count `ν`** | `n − log₂(log|zₙ|)`: a continuous version of the step count. |
| **View** | `(cx, cy, w)`: the centre and width of the visible part of the plane. |
