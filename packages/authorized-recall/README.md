# Authorized Recall@K

**Retrieval quality measured over the subset a principal may actually use.**

This package has no dependency on the rest of the repository. The metric takes
a predicate, not a `Principal`, so a system using RBAC, ABAC, row-level
security or per-tenant vector namespaces can adopt the measurement without
adopting anything else here.

```
python -m authorized_recall
```

---

## Why

A retrieval system that surfaces a dataset the caller is not permitted to use
has not helped them. They cannot act on it; the only thing that changed is that
they now know it exists. Standard Recall@K scores that as a success, and it has
also spent one of the K slots doing it.

In the corpus measured here, **68.8% of what retrieval returns is unusable to
the principal who asked**, and Recall@K cannot see it.

## Definition

Let

- $D$ — the corpus,
- $q$ — a query, with relevant set $R(q) \subseteq D$,
- $p$ — a principal, with authorization predicate $A_p : D \to \{0,1\}$,
- $L_K(q,p)$ — the ordered list of at most $K$ items the system returns.

The **authorized relevant set** is

$$R_A(q,p) = \{\, d \in R(q) : A_p(d) = 1 \,\}$$

and

$$\mathrm{ARecall}@K(q,p) = \frac{|R_A(q,p) \cap L_K(q,p)|}{|R_A(q,p)|},
\qquad \mathrm{ARecall}@K \triangleq 1 \ \text{ when } R_A = \emptyset .$$

Compare

$$\mathrm{Recall}@K(q) = \frac{|R(q) \cap L_K|}{|R(q)|} .$$

**When $A_p \equiv 1$, $\mathrm{ARecall}@K = \mathrm{Recall}@K$.** The metric is
a strict generalisation, not a different measurement.

### Two conventions, stated because they change the mean

1. $R_A = \emptyset \Rightarrow \mathrm{ARecall}@K = 1$. The system cannot be
   faulted for failing to surface what it must not surface. Over a population
   containing such pairs this inflates the mean, so report the restricted mean
   — over pairs with $R_A \neq \emptyset$ — alongside it. The experiment here
   prints both.
2. Retrieved-but-unauthorized items are neither credited nor penalised inside
   ARecall. They are a separate quantity:

$$U@K(q,p) = \frac{|\{\, d \in L_K : A_p(d) = 0 \,\}|}{K}$$

## Where the filter sits

ARecall is computed over the list the system **returns**, so it is sensitive to
whether truncation happens before or after the authorization filter:

$$L_K^{\text{post}} = \sigma_{A_p}\big(\mathrm{top}_K(\mathrm{rank}(D))\big)
\qquad
L_K^{\text{pre}} = \mathrm{top}_K\big(\sigma_{A_p}(\mathrm{rank}(D))\big)$$

**Claim.** $L_K^{\text{post}} \subseteq L_K^{\text{pre}}$ for every ranking,
$K$ and $A_p$, hence

$$\Delta@K = \mathrm{ARecall}^{\text{pre}}@K - \mathrm{ARecall}^{\text{post}}@K \;\geq\; 0 .$$

*Proof.* Filtering preserves relative order. An item in $L_K^{\text{post}}$ is
authorized and appears within the first $K$ positions of the ranking, so at
most $K-1$ items precede it, so at most $K-1$ *authorized* items precede it,
so it appears within the first $K$ authorized items — which is
$L_K^{\text{pre}}$. ∎

The gap is therefore non-negative by construction rather than by luck of the
corpus. What the corpus determines is its *size*.

## Measured

40 synthetic datasets over 8 domains, 24 queries, 4 authorization profiles,
96 query-principal pairs. Relevance by construction: a dataset is relevant to a
query when it is in the query's domain. Retrieval is TF-IDF cosine.

```
  K   Recall  ARecall  ARecall    gap  unusable
                 post      pre         in top-K
  1    0.200    0.750    0.750 +0.000     68.8%
  3    0.483    0.835    0.863 +0.027     68.8%
  5    0.867    0.954    0.988 +0.033     68.5%
 10    1.000    1.000    1.000 +0.000     39.1%
```

Restricted to the 30 pairs with $R_A \neq \emptyset$:

```
  K  ARecall post  ARecall pre     gap
  1         0.200        0.200  +0.000
  3         0.473        0.560  +0.087
  5         0.853        0.960  +0.107
 10         1.000        1.000  +0.000
```

**At K=5, moving the filter ahead of truncation takes ARecall@5 from 0.853 to
0.960 (+0.107). Recall@5 stays at 0.867 and cannot see the difference.**

## What this does and does not establish

The absolute values belong to this corpus: relevance is by construction, the
retriever is TF-IDF, and MRR is 1.000, so the retrieval task is easy. A harder
corpus or a better retriever moves all three columns.

The *gap* is what the metric was defined to isolate, and the claim above is
that it is a property of filter placement rather than of retrieval quality. The
proof makes its sign certain; the experiment gives its size in one setting.

Applying it to a real corpus with real authorization data is the obvious next
measurement, and this package is separable precisely so that someone else can
do it.
