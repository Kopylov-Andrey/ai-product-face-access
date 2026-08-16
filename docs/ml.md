# ML-дизайн системы распознавания лиц

## 1. ML Pipeline

```
camera frame → detection → quality assessment → alignment
  → liveness/PAD → embedding extraction → ANN identification (1:N)
  → threshold + margin logic → policy validation → decision
```

Каждый компонент — ML inference или deterministic rule.

## 2. Verification (1:1) vs Identification (1:N)

**Verification (1:1):** проверка claimed identity. Сравнение с одним reference. Fast, lower false match risk. Требует заявленную identity (например, card).

**Identification (1:N):** поиск без заявленной identity среди N сотрудников. Slower при exhaustive, higher risk при большом N.

**Выбор:** основной режим — **identification (1:N)** face-only. Card fallback теоретически позволяет 1:1 verification, но не является частью automatic biometric happy path.

**Metrics distinction:**

| Mode | Metrics |
|------|---------|
| 1:1 Verification | FMR (False Match Rate), FNMR (False Non-Match Rate) |
| 1:N Identification | FPIR (False Positive Identification Rate), FNIR (False Negative Identification Rate), Rank-K accuracy |

**Product/safety level:** используем FAR/FRR terminology (более понятные), но **system-level 1:N evaluation must use FPIR/FNIR и identification metrics**. FPIR scales with N (12,000 employees).

## 3. ANN (Approximate Nearest Neighbor) Index

**Проблема exhaustive:** 12k embeddings × O(N) comparison непрактично для latency target.

**Решение: ANN index** (FAISS, HNSW, Annoy — выбор implementation-dependent, requires benchmark).

**Target design:**
1. ANN top-K retrieval (K=5–10 candidates)
2. Exact similarity re-ranking retrieved candidates
3. Threshold logic: T_allow / T_review + second-best margin
4. Insufficient confidence ⇒ MANUAL_REVIEW / CLOSED

**Не заявляем automatic exhaustive search fallback** на каждый hot-path miss (latency prohibitive).

**Exhaustive exact search** используется offline/shadow как benchmark для измерения ANN recall и threshold behavior.

**ANN/index quality uncertainty → fail closed.**

## 4. Threshold Calibration

**Требуется multiple thresholds:**

- **T_allow:** high confidence для auto-open
- **T_review:** borderline → manual review
- **Margin:** minimum difference между top-1 и top-2 scores (unique match)
- **T_liveness:** PAD threshold
- **T_quality:** technical quality gates

**Threshold values НЕ изобретаются.** Calibrated на validation data с учётом:
- Target FRR ≤3% pilot
- FPIR minimization
- Manual review rate ≤1%
- Asymmetric costs: FA >> FR (security incident vs 10s retry)

**Decision pseudo-code:**

```python
if quality < T_quality:
    return RETRY

if liveness < T_liveness:
    return DENY if suspected_spoof else RETRY

top1, top2 = ann_top2_then_exact_rerank(embedding)

if top1.score < T_review:
    return MANUAL_REVIEW

if top1.score >= T_allow:
    margin = top1.score - top2.score
    if margin < T_margin:
        return MANUAL_REVIEW  # ambiguous
    
    if policy_fresh() and policy_valid(top1.employee_id):
        return ALLOW
    elif policy_stale():
        return NO_AUTO_ALLOW  # degraded
    else:
        return DENY  # revoked
else:
    return MANUAL_REVIEW
```

**Asymmetric costs:** FA = security incident (500k+ ₽). FR = 10s retry + UX friction. Threshold selection prioritizes security while guardrails control FRR/review-rate.

## 5. Validation Design

**CRITICAL: split by identity/person, не by frames.** Frames одного человека в train+validation ⇒ data leakage, unrealistic FRR.

**Coverage requirements:**
- Multiple cameras, days, lighting conditions
- Occlusions: masks, glasses, headwear
- Demographic subgroups (если legal/available) для bias detection
- PAD attack samples: printed photos, screen/video replay

**Per-condition metrics:** FRR by camera/lighting/occlusion, не только aggregate. Выявляет systematic bias.

**Prevent leakage:** employee template updates, temporal drift, registry changes не попадают в validation как "новые" данные.

## 6. Metrics

**Biometric (1:N identification):**
- FPIR / FNIR (system-level 1:N metrics)
- FAR / FRR (product-level terminology, понятнее stakeholders)
- ROC/DET curves для threshold selection
- Rank-1 identification accuracy

**Liveness/PAD:**
- APCER (attack pass rate), BPCER (genuine reject rate)
- Per-attack-type metrics

**System:**
- Manual review rate ≤1% pilot
- Latency p50/p95/p99
- Throughput passages/min

## 7. Delayed Labels

Ground truth labels приходят асинхронно:

1. **Guard review outcome:** manual review → guard decision, joined via event_id
2. **Employee complaints:** "система не пустила" → false reject signal
3. **Successful fallback:** employee прошёл по карте после biometric reject → FR signal
4. **Confirmed security incidents:** forensic review → potential FA

**Используются для:** threshold recalibration, model retraining, continuous monitoring drift.

## 8. Liveness/PAD

**Baseline: layered passive PAD** (no user action required) + quality checks.

**Threat model:**

| Attack | In Scope | Mitigation |
|--------|----------|------------|
| Printed photo (color/B&W) | ✅ | Texture, depth, quality |
| Screen replay (phone/tablet/laptop) | ✅ | Moiré, reflectance |
| Video replay | ✅ | Depth, micro-movements |
| 3D mask (high-quality) | ⚠️ Candidate future | Difficult, requires advanced PAD |

**Не заявляем perfect spoof protection.** PAD — arms race. **Uncertain PAD result → CLOSED** (fail safe).

## 9. LLM в Системе

**Explicit: LLM НЕ используется для detection, matching, liveness или allow/deny.**

**Причины:**
1. Non-determinism несовместим с safety audit для физического доступа
2. Latency (сотни ms - секунды) нарушает target ≤1 с
3. Unnecessary: детерминированная CV pipeline + rule engine достаточны
4. Hard safety requirements: provable invariants (INV-1..6) нельзя гарантировать с LLM
5. Auditability: forensic review требует reproducible decisions

**Potential future use (НЕ в критическом пути):** incident summarization для operators, но **не может override** deterministic engine.

## 10. Model Selection и Licensing

**Не изобретаем benchmark numbers.** Процесс: survey SOTA → benchmark на validation → pilot measurement.

**Candidate pretrained models (для evaluation, НЕ commitment):**
- Embedding: InsightFace-family, ArcFace-based, FaceNet
- Detection: RetinaFace, MTCNN, BlazeFace
- Liveness: Silent-Face-Anti-Spoofing, FAS-based

**ВАЖНО: research availability ≠ production licensing approval.**

Specifically, **InsightFace-family models** и другие research pretrained assets **require license validation** before commercial/production use. Legal/compliance review mandatory.

Final choice: benchmark-driven, validated в pilot.

## 11. Continuous Learning

**Template drift:** aging, hairstyle, facial hair. Periodically request re-enrollment (operational policy, not invented cadence) или accumulate high-confidence ALLOW → auto-update template (с approval).

**Model retraining:** collect production data (с consent/legal), retrain на updated data, versioned deployment, canary rollout.

**Threshold recalibration:** monitor delayed labels, re-tune на updated validation.

## 12. MVP vs Target

**MVP:** deterministic decision logic, mock CV (random scores), synthetic events. Цель: prove architecture + safety, не ML accuracy.

**Target:** pretrained CV stack, calibrated thresholds на validation, production ANN (12k), real employee cohort. Цель: validate FRR/FPIR, measure latency.

## 13. Ключевые ML Решения

1. **Identification (1:N)** face-only, не verification (1:1) с картой
2. **ANN + exact re-ranking** вместо exhaustive hot-path search
3. **FPIR/FNIR metrics** для system-level 1:N evaluation
4. **Multiple thresholds + margin** вместо single threshold
5. **Split by identity** validation, prevent leakage
6. **Per-condition metrics** detect bias
7. **Asymmetric cost-driven** threshold selection
8. **Passive PAD baseline**, fail closed на uncertain
9. **Delayed labels** integration для continuous monitoring
10. **No LLM в critical path:** deterministic, auditable, low-latency
11. **Licensing validation mandatory** для production pretrained models
