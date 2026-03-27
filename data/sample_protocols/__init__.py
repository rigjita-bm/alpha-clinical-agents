"""
Sample Clinical Protocol: Phase III Oncology Study
Anonymized for educational purposes
"""

ONCOLOGY_PHASE3_PROTOCOL = """
CLINICAL STUDY PROTOCOL

Protocol Number: PROTO-2026-001
Version: 3.0
Date: January 15, 2026

Title:
A Randomized, Double-Blind, Placebo-Controlled, Phase 3 Study of AlphaBlock 
in Combination with Standard Chemotherapy in Patients with Metastatic 
Non-Small Cell Lung Cancer (NSCLC)

STUDY DESIGN
This is a multicenter, randomized, double-blind, placebo-controlled, 
phase 3 study evaluating the efficacy and safety of AlphaBlock in 
combination with standard chemotherapy (carboplatin and paclitaxel) 
compared to placebo plus chemotherapy in patients with metastatic NSCLC.

Randomization will be stratified by:
- ECOG performance status (0 vs 1)
- Histology (squamous vs non-squamous)
- Prior therapy lines (0 vs 1)

OBJECTIVES

Primary Objective:
- To evaluate the efficacy of AlphaBlock plus chemotherapy vs placebo 
  plus chemotherapy as measured by overall survival (OS)

Secondary Objectives:
- To evaluate progression-free survival (PFS)
- To evaluate objective response rate (ORR) per RECIST 1.1
- To evaluate duration of response (DOR)
- To evaluate safety and tolerability
- To evaluate quality of life (QoL)

ENDPOINTS

Primary Endpoint:
- Overall survival (OS) defined as time from randomization to death 
  from any cause

Secondary Endpoints:
- Progression-free survival (PFS) per RECIST 1.1 by investigator assessment
- Objective response rate (ORR) defined as proportion with CR or PR
- Duration of response (DOR) for responders
- Safety: Incidence of adverse events (AEs), serious AEs, Grade ≥3 AEs
- Patient-reported outcomes using EORTC QLQ-C30 and LC13

STUDY POPULATION

Planned Enrollment:
Approximately 600 patients will be randomized in a 1:1 ratio:
- Arm A (AlphaBlock + chemotherapy): 300 patients
- Arm B (Placebo + chemotherapy): 300 patients

Key Inclusion Criteria:
1. Histologically or cytologically confirmed metastatic NSCLC
2. No prior systemic therapy for metastatic disease
3. ECOG performance status 0 or 1
4. Measurable disease per RECIST 1.1
5. Life expectancy ≥ 3 months
6. Adequate organ function:
   - Absolute neutrophil count (ANC) ≥ 1.5 × 10^9/L
   - Platelets ≥ 100 × 10^9/L
   - Hemoglobin ≥ 9 g/dL
   - Creatinine clearance ≥ 60 mL/min
   - Total bilirubin ≤ 1.5 × ULN
   - AST/ALT ≤ 2.5 × ULN (≤ 5 × ULN if liver metastases)

Key Exclusion Criteria:
1. Known EGFR mutation or ALK rearrangement (should receive targeted therapy)
2. Active or untreated brain metastases
3. Autoimmune disease requiring systemic therapy
4. Prior therapy with checkpoint inhibitors
5. Uncontrolled intercurrent illness
6. Pregnancy or breastfeeding

TREATMENT

Duration:
Treatment will continue until:
- Disease progression per RECIST 1.1
- Unacceptable toxicity
- Patient withdrawal of consent
- Investigator discretion

Maximum duration: 24 months

STATISTICAL METHODS

Sample Size Calculation:
Based on an assumed median OS of 12 months in control arm and 16 months 
in experimental arm (HR = 0.75), with 90% power and two-sided alpha of 0.05,
requiring 450 events. Accounting for 10% dropout, total 600 patients needed.

Primary Analysis:
OS will be analyzed using stratified log-rank test with HR and 95% CI 
estimated using stratified Cox proportional hazards model.

Interim Analysis:
One interim analysis for efficacy will be conducted at approximately 60% 
of total events using O'Brien-Fleming spending function.

Secondary Analyses:
- PFS: Stratified log-rank test, Kaplan-Meier estimates
- ORR: Cochran-Mantel-Haenszel test with stratification factors
- Safety: Descriptive statistics, incidence rates

DATA MONITORING

Independent Data Monitoring Committee (IDMC) will review unblinded 
safety and efficacy data at scheduled intervals.

REGULATORY COMPLIANCE

This study will be conducted in accordance with:
- ICH E6 Good Clinical Practice (GCP)
- Declaration of Helsinki
- 21 CFR Part 11 (electronic records)
- Local regulatory requirements

All patients must provide written informed consent before any study 
procedures.
"""

CARDIOLOGY_PHASE2_PROTOCOL = """
CLINICAL STUDY PROTOCOL

Protocol Number: CARD-2026-002
Version: 2.0
Date: February 1, 2026

Title:
A Randomized, Double-Blind, Phase 2 Study of BetaHeart in Patients 
with Heart Failure with Reduced Ejection Fraction (HFrEF)

STUDY DESIGN
Multicenter, randomized, double-blind, placebo-controlled, parallel-group 
phase 2 study to evaluate efficacy, safety, and tolerability of BetaHeart 
in patients with chronic HFrEF.

OBJECTIVES

Primary Objective:
Evaluate effect of BetaHeart on exercise capacity measured by 
cardiopulmonary exercise testing (CPET) at Week 24.

Secondary Objectives:
- Evaluate effect on NT-proBNP levels
- Evaluate effect on 6-minute walk test (6MWT)
- Evaluate effect on Kansas City Cardiomyopathy Questionnaire (KCCQ)
- Evaluate safety and tolerability

ENDPOINTS

Primary Endpoint:
Change from baseline in peak oxygen uptake (VO2 max) at Week 24

Secondary Endpoints:
- Change from baseline in NT-proBNP at Week 12 and 24
- Change from baseline in 6MWT distance
- Change from baseline in KCCQ total symptom score
- Time to first heart failure hospitalization
- All-cause mortality
- Safety endpoints: AEs, SAEs, lab abnormalities

STUDY POPULATION

Planned Enrollment: 240 patients (120 per arm)

Key Inclusion Criteria:
1. Age 18-80 years
2. Chronic heart failure ≥ 3 months
3. LVEF ≤ 35% (confirmed by echocardiography within 60 days)
4. NYHA Class II-III
5. On stable guideline-directed medical therapy (GDMT) for ≥ 30 days:
   - ACE inhibitor or ARB or ARNI
   - Beta-blocker (unless contraindicated)
   - MRA (if indicated)
6. NT-proBNP ≥ 400 pg/mL (or BNP ≥ 100 pg/mL)
7. Hemoglobin ≥ 10 g/dL

Key Exclusion Criteria:
1. Systolic blood pressure < 90 or > 160 mmHg
2. Heart rate < 50 bpm or > 110 bpm
3. eGFR < 30 mL/min/1.73m²
4. Severe hepatic impairment (Child-Pugh C)
5. Active myocarditis or pericarditis
6. Planned cardiac surgery or device implantation
7. Participation in another interventional study

STATISTICAL METHODS

Sample size based on ability to detect 2.0 mL/kg/min difference in 
VO2 max (SD = 4.5) with 85% power and alpha = 0.05.

Primary analysis: ANCOVA with baseline VO2 max as covariate.

Missing data: Multiple imputation assuming missing at random.
"""

RARE_DISEASE_PHASE2_PROTOCOL = """
CLINICAL STUDY PROTOCOL

Protocol Number: RARE-2026-003
Version: 1.0
Date: March 1, 2026

Title:
An Open-Label Phase 2 Study of GammaCure in Patients with 
Glycogen Storage Disease Type II (Pompe Disease)

STUDY DESIGN
Multicenter, open-label, single-arm phase 2 study to evaluate efficacy 
and safety of GammaCure enzyme replacement therapy in patients with 
late-onset Pompe disease.

Special Considerations for Rare Disease:
- Small population (estimated 1 in 40,000)
- Natural history data used as historical control
- Adaptive design allowing dose modification
- Long-term follow-up (5 years)

OBJECTIVES

Primary Objective:
Evaluate effect of GammaCure on 6-minute walk distance (6MWD) at Week 52.

Secondary Objectives:
- Evaluate effect on forced vital capacity (FVC)
- Evaluate effect on GAA enzyme activity
- Evaluate biomarker response (CK, hexose tetrasaccharide)
- Evaluate safety in this rare population
- Assess quality of life using SF-36

ENDPOINTS

Primary Endpoint:
Change from baseline in 6-minute walk distance at Week 52

Secondary Endpoints:
- Change from baseline in FVC % predicted (upright and supine)
- GAA enzyme activity in dried blood spots
- Serum creatine kinase (CK) levels
- Urine hexose tetrasaccharide levels
- SF-36 physical component summary score
- Safety: AEs, SAEs, infusion-associated reactions (IARs)

STUDY POPULATION

Planned Enrollment: 30 patients

Given the rarity of Pompe disease, this study uses:
- Multi-regional recruitment (US, EU, Japan)
- Expanded access program for non-responders
- Natural history comparison group

Key Inclusion Criteria:
1. Confirmed diagnosis of late-onset Pompe disease (GAA deficiency)
2. Age ≥ 18 years
3. Able to walk ≥ 75 meters in 6-minute walk test
4. FVC ≥ 30% predicted (upright)
5. No prior enzyme replacement therapy (naive patients)

Key Exclusion Criteria:
1. Infantile-onset Pompe disease
2. Requirement for invasive ventilation
3. Severe orthopedic deformities limiting mobility assessment
4. Concurrent immunosuppressive therapy
5. Pregnancy or plans to become pregnant

TREATMENT

GammaCure 20 mg/kg administered by intravenous infusion every 2 weeks.

Premedication for IARs:
- Antihistamine (e.g., diphenhydramine)
- Antipyretic (e.g., acetaminophen)
- Optional corticosteroid

Infusion rate escalation protocol for first infusion.

STATISTICAL METHODS

Given small sample size:
- Primary analysis: Paired t-test or Wilcoxon signed-rank
- Mixed effects model for repeated measures
- 95% confidence intervals reported (not p-values)
- Comparison to natural history data (propensity score matched)
- Bayesian analysis with informative priors from Phase 1

Interim Analysis:
One interim analysis at n=15 patients (Week 26 data) for futility.

DATA SHARING
- Aggregated results shared with patient advocacy groups
- Individual patient data available to qualified researchers
- Results published regardless of outcome
"""
