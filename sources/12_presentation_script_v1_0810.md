# MASIL 결선 발표 대본 — 1차 최종본 (2026-08-10)

상태: 현재 발표자 배분과 발화 흐름을 반영한 1차 최종 대본. Q&A 검색에서 질문 표면과 쉬운 영어 표현 재료로 사용한다. 상품 사실·수치·문헌 범위가 현재 정본과 충돌하면 product_model, active official position, 최신 덱 교정 상태가 우선한다.

## 정본 적용 메모

- `Pay-As-You-Drive (PAYD)`는 얼마나 운전했는지, UBI는 어떻게 운전했는지, MASIL은 개인 생활권과 평소 대비 변화까지 본다고 설명한다.
- Favorable·Standard·Care는 월별 결과다. 최신 대시보드의 두 사람 연간 비교는 Care·Favorable 등급이 아니라 Annual average score 81.6·98.4를 보여준다.
- 월별 Care는 그 달의 검토·지원 신호이고, 연간 할인율은 연간 주행 기록으로 별도 계산한다.
- 생활권 밖이라는 위치 자체에는 벌점이 없다. 현재 팀 후보식은 밖에서 실제 발생한 위험 이벤트를 더 민감하게 보지만, 기존 Edward·Frank와 180개 시나리오 수치는 8/8 실행 결과이므로 8/12 결과라고 설명하지 않는다.
- 2.28초·90%는 시야가 제한된 돌발 상황의 조건부 결과다.
- Pilot → Scale up → Roll out의 방향만 확정 설명에 사용한다. 대본의 기간·500명·15~20%·+2%p·30~50대 확대는 발표 확정 수치로 사용하지 않는다.
- 사고 감소·손해율 개선·가족 부담·사회비용 감소는 검증된 성과가 아니라 파일럿 가설이다.

1. SUMMARY 1 (다현) - 4분
0. Opening — about 15 sec
   Hello everyone.
   We are FourSure, from South Korea.
   Today, we would like to introduce our solution,
   the Senior MASIL Zone Rider.

Our idea is simple.
For senior drivers, risk is not only about how much they drive,
but also where they drive and how their driving patterns change.
—
Before we begin, you can scan the QR code on the upper right corner
to check out our dashboard.
It provides a more intuitive understanding of the MASIL rider.

1. SUMMARY — Problem & Solution

Let me start with the problem.
Why do we need a different approach for senior drivers?

First, accidents involving senior drivers are increasing.
In Korea, overall traffic accidents decreased,
but senior driver accidents increased by over 8 percent.
So this is becoming a growing risk.

But this is not just about inattention.
For senior drivers, situational judgment is critical.
For example, braking reaction time is about 2.28 seconds,
90 percent slower than younger drivers.

Furthermore, many accidents happen at intersections or during yielding.

So the issue is not only
“Are they paying attention?”
but also
“Can they make immediate right decisions in complex situations?”

Another key factor is familiarity.
Risk changes depending on how familiar the location is.
Research shows first-time routes can have 2.5 times higher crash risk.
So even if two drivers travel the same distance,
their risk levels can be very different.

However, current regulations and insurance products
do not fully reflect this issue.
Conditional licenses can limit the mobility of seniors.
At the same time, license renewal alone
cannot capture changes in driving risk between periods.
In other words,
If we restrict driving, it can lead to concerns about mobility rights.
But if we rely only on periodic checks,
we cannot reflect each individual’s real driving risk in detail.
MASIL offers a new approach from the insurer’s perspective.
It aims to achieve both safety and mobility at the same time.
Yet, existing insurance products
still fail to properly address this balance.
Pay-As-You-Drive reflects how much you drive,
and UBI reflects how you drive,
but neither fully captures where a senior driver is comfortable
or when their driving pattern changes.

So we ask:
“Can we evaluate senior drivers based on how they actually drive?”

---

This is where MASIL Zone comes in.

“Masil” is a Korean word meaning
a short, familiar trip around one’s neighborhood.
It reflects how most senior drivers actually drive.

A MASIL Zone is a personalized activity zone
based on repeated visits over a two-month baseline.
By clustering destinations visited on at least three different days,
we define the Core Zone.
Then, using the 90th percentile, we expand it into a Buffer Zone
and everything beyond that falls into the Outer Zone.

In simple terms,
it represents where the driver feels familiar and comfortable.

---

We then combine this with four factors:

Mileage — how much they drive
In-Zone Safety — safety in familiar areas
Out-Zone Safety — safety in unfamiliar areas
Pattern Change — changes in driving behavior

To be clear, risky driving outside the zone matters more.

Together, these are combined into one MASIL Score,
which determines three tiers: Favorable, Standard, and Care,
linked to premium discounts.

---

So our message is simple:
MASIL is not an insurance product
that restricts senior drivers.
It rewards those who drive safely
in familiar areas.
And for those showing risk signals,
it intervenes before accidents happen.
In short, it is a proactive risk management system.


In other words,
we are not asking drivers to fit insurance.
We are making insurance fit their real life.


2. 대시보드 + SUMMARY 2 (AI pipeline+Data Stardards) (은서) - 4분

2. DASHBOARD — Quick Introduction
Let me briefly show how MASIL works in practice.
This is Edward Clark’s dashboard.
Edward is currently classified as Care this month.
Staff can see his MASIL Zone, driving behavior, and the reasons behind his grade.
For example, let’s compare Edward with Frank Wilson.
Under the current mileage-based scheme,
they look almost the same.
Same vehicle class.
Same tariff.
Similar annual mileage.
So today, they pay the same premium.
But MASIL sees a different risk.
Edward has 209 risky events,
while Frank has only 10.
Their safety scores also differ
both inside and outside their familiar zones.
Importantly, MASIL does not treat leaving the familiar zone itself as risky.
Instead, it looks for changes from usual driving combined with risky behavior.
That is why Edward receives only a 3% discount,
while Frank receives 22.6%.
Same conditions, different risk —
because MASIL looks at how driving behavior changes,
both inside and outside the familiar zone.
The monthly view also shows
whether these signals are a one-time event
or a pattern developing over time.
After reviewing the report,
the staff member can approve the result.
Edward can then check his grade in the app
and apply for Care support if needed.
So MASIL connects
risk assessment, insurance decisions, and actual support.

Now, let me explain how we tested the idea.
We built an AI-assisted simulation pipeline.
First, we generated synthetic GPS data
based on different senior driver profiles.
Then, DBSCAN and P90 created each driver’s MASIL Zone.
Next, we ran the simulation
and applied our rule-based grading:
Favorable, Standard, or Care.
Each result comes with Reason Codes.
These codes are shown in the final report,
so we can clearly explain the result.
And importantly,
AI does not decide the premium.
AI helps create realistic driver profiles and movement patterns.
The grading and Reason Codes
come from fixed, explainable rules.
We also incorporated existing driving standards and accident statistics.
For validation, we created 60 simulated drivers
across six driver types and three regions,
resulting in 180 scenarios of driving data.
We used the previous two months as the baseline
and evaluated each driver over the following 12 months.
Our goal was not to represent real customers,
but to test whether our product logic works as intended.
This framework can later be validated
with real driving data.


3. SUMMARY 2 (Result + Pilot~ + Closing 멘트) (진영) - 3분

4. RESULT
So, what does MASIL achieve?
For society,
 road safety is important.
At the same time,
 many senior drivers want to preserve their mobility.
This creates
 a difficult dilemma.
Regulation can support safety,
 but stronger restrictions may limit mobility.
This is where we focused
 on the role insurance can play.
MASIL offers another way
 to support safer driving
 without limiting senior drivers’ mobility.

And this approach creates value
 for four key groups.

First, insurers.
MASIL can detect changes in driving risk
 before an accident happens.
This allows insurers
 to provide preventive care earlier.
It can also find risks
 that mileage alone may miss.
So insurers can manage risk better
 and offer discounts more precisely.
Second, senior drivers.
Safe and stable drivers
 can qualify for a larger discount.
They can also see changes
 in their own driving patterns.
And if their risk begins to increase,
 they can receive preventive support earlier.
Third, family.
With the driver’s consent,
 safety information can be shared
 with family members.
Real-time location
 does not need to be shared.
This can reduce
 the family’s worry
 and caregiving burden.
And fourth, society.
MASIL can help build
 a voluntary, private-led safety system.
This can help reduce accidents
 and, in the long term,
 reduce social costs.
5. Roadmap / Next Steps
Finally, let me show you
 our next steps.
In the first 6 months,
 we will test MASIL
 with real driving data.
Then, up to 18 months,
 we plan a limited launch
 for senior drivers.
After 18 months,
 we plan to expand MASIL
 to drivers aged 30 to 50.
So MASIL starts with senior drivers,
 but it can grow into
 a wider insurance model
 for safer driving.
6. Closing
Finally, I would like to leave you
 with one question.
Should the answer be
 to reduce senior drivers’ mobility?
Or should we help people
 who still need to drive
 move more safely?
We believe the answer is the second.
The same mileage
 does not always mean the same risk.
That is why we propose MASIL.
Thank you.
