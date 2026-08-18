1. SUMMARY 1 (다현) - 5분 30초
0. Opening
Hello everyone.


Before we start,
I want to teach you one special word in Korean.

 MASIL
“MASIL” means a short, familiar trip around one’s neighborhood.
It could be a trip to the grocery store, hospital, or a local church.
It’s usually used by our grandparents, saying,
“I’m going out on a masil.”

So, from now on,
the area where each senior frequently travels and feels familiar is the “MASIL Zone.”

Based on this concept, we created our solution: Senior MASIL Zone Rider.

For senior drivers, going out to masil helps seniors stay active, independent, and socially connected.
How many of you have parents who still drive today?

My grandfather is 82 this year, and he still drives to the senior community center once in a while.

He usually drives safely on his familiar route.
But has some difficulties when he is not in his MASIL.

This is where we found a new opportunity.
Every senior has different MASILs and driving patterns.
Therefore, the big question we came up with was:

“What if insurance could understand each senior’s familiar driving area — and evaluate their driving in that personal context?”

This is the core idea of MASIL Zone rider.

1. Problem & Solution
But then,
Do current systems and insurance products capture these individual differences?

Today, senior drivers are managed through regulations like conditional licenses and prolonged renewals.

But license restrictions limit mobility, while periodic checks may miss changes between checkups.

Insurance also has limitations.

Pay-As-You-Drive looks at how much you drive.
Usage Based Insurance looks at how you drive.

The problem is that current approaches cannot distinguish the different risks of each senior driver.

Then, why do we need to distinguish these personalized zones and changes for senior drivers?

First, the need for better senior driver risk management is growing.

The share of older people worldwide is expected to grow from 10% to 16% by 2050.
In Korea, accidents involving senior drivers also increased by about 8%.

But the important point is: The risk is not the same for every senior driver.

One difference of seniors that stands out the most
 is familiarity with the route.

One study found that crash risk was 2.5 times higher on unfamiliar routes
than on familiar ones.

Another study found that route familiarity also influenced choice.
76% preferred the familiar route even when a low-risk alternative was available.


This tells us that familiarity matters.

But, what is “usual” can differ from driver to driver.
So, each driver needs their own baseline to detect changes in their driving pattern.
—-
Many seniors still drive to maintain their daily lives and independence
and 86% of them hope to keep their mobility rights.


So what we need is not more restrictions.
We need a more precise way to understand each driver's real driving.

To solve this, we designed our rider.

Remember the word I mentioned at the very beginning?

“MASIL Zone”

Let me explain in more detail
and how we define it for each senior driver.

MASIL Zone is a personalized activity zone based on repeated visits over a two-month baseline.

It is defined by clustering destinations visited on at least three different days and using the 90th percentile,


We then combine this with four factors
to calculate an integrated score for each driver.

Mileage — how little they drive.
In-Zone Safety — safety in familiar zones.
Out-Zone Safety — safety in unfamiliar zones.
Pattern Change — stable driving patterns.

Together, these factors create a monthly integrated score,
which determines three tiers: Favorable, Standard, and Care.
Favorable drivers receive the highest refund,
while Care drivers receive safety feedback and closer monitoring.
The annual score averages the 12 monthly scores and determines the final refund.
Drivers who achieve Favorable for more than 9 months
can receive an additional refund.

And there is one important point.

Going outside the MASIL Zone does not automatically mean higher risk.
If a driver is safe and stable in their familiar area, we reward that behavior.

But if they start driving outside their MASIL Zone and show other risk signals,
we immediately step in to analyze the situation
So, Senior MASIL Zone Rider looks beyond
how much seniors drive
and how they drive.

Where are they driving?
And, What has changed from their normal pattern?
That is what makes MASIL different.









2. 대시보드 + SUMMARY 2(AI pipeline+Data Standards) (은서) - 3분 30초(최선…)

DASHBOARD — Quick Introduction
Now, let me show how MASIL Zone Rider works in practice.
You can see how it works on our live dashboard.
The screen here is just an example.
You can also scan the QR code on the upper right
to see our live dashboard.
First, this is Jackie Chan’s dashboard.
We all know Jackie Chan as a famous action star, full of energy.
But he is now over 70, so in this example, we use him as a senior driver.

Here, staff can review his monthly score and driving record.
For example, his July score is 76 points.
We can also check his record month by month for one year,
and see changes in his driving pattern.
In this example, he was rated Favorable until June,
but in July, his risk increased.
Even a stable driver like Jackie can show these changes.
That is why early detection matters.

MASIL Zone Rider also helps us see each driver’s different risks.
Now, let’s compare Jackie with his friend, Tom Hanks, another senior driver.
Under the current Pay as you drive system, their similar mileage leads to the same refund.
But their driving tells a different story.
Jackie became more risky as his driving pattern changed.
Tom stayed stable despite driving outside his usual area.
With MASIL Zone Rider, they receive different refunds.
Jackie receives only a 3% refund, while Tom receives 22%.
This provides a more personalized refund, even with similar mileage.

The results are summarized in the final report.
After reviewing the report, staff can approve his monthly grade and annual refund.
Jackie can then check his result every month in the app.
This helps him understand his driving and make safer changes over time.
He can also apply for Care support if needed.

SUMMARY 2- AI-ASSISTED SIMULATION PIPELINE
Now, let me explain how we validated our idea.
We built an AI-assisted simulation pipeline.
We created 180 driving scenarios,
with six senior driver types and three regions.
We generated simulated GPS data based on each driver profile,
using existing driving-behavior standards
and public accident statistics to make it realistic.
Then, we combined DBSCAN clustering with P90 to create each driver’s MASIL Zone.
Next, we applied our fixed rules to assign three tiers:
Favorable, Standard, or Care.
The grade and refund are determined by fixed, explainable rules.
The LLM only turns the reasons into a simple explanation for the report.
For evaluation, we used the previous two months as the baseline for each month.
At this stage, we used simulated data to validate the product logic.
In the future, we will first validate MASIL with real-world driving data from a pilot cohort.

If the rider is implemented commercially, insurers can use accumulated customer data to further refine the scoring and risk assessment.
Once the rider is launched, insurers can use accumulated customer data to further refine the scoring and risk assessment.
(Over time, MASIL can also connect drivers with preventive services through public and healthcare partnerships.)

3. SUMMARY 2 — Roadmap → Value Cycle → Closing(진영) - 2분 5
0초
So what does masil acheive?
MASIL can create a value cycle for safer mobility.
For insurers,
 MASIL can support profitability through better loss ratio management.
MASIL gives insurers a clearer view of each driver’s risk.
 This can support more accurate pricing.
 It can also make MASIL more attractive to lower-risk drivers
 and help reduce adverse selection.
MASIL can also identify driving risks earlier.
Unlike traditional insurance that responds after an accident, this gives insurers a chance to intervene before those risks lead to claims.
All of this can help lower the loss ratio.
MASIL also creates long-term data value.
 Over time, accumulated driving data can help improve MASIL’s risk assessment.
 It can also help insurers match preventive services to different risk patterns.
 And it can support better risk models and future product design.
For senior drivers,
 MASIL can offer more tailored refunds by reflecting each driver’s risk more precisely.
More importantly, MASIL gives drivers feedback on their driving risk
 and changes in their driving patterns.
 This helps them respond before the risk becomes more serious
 and stay mobile while driving more safely.
MASIL can also create value for society.
 By encouraging safer choices,
 it can help create a safer mobility environment.
Together, these benefits create a value cycle —
 better risk management for insurers,
 safer mobility for senior drivers,
 and a safer society.

Finally, I’d like to leave you with one message.
As our society ages, senior drivers will become a larger and more diverse group.
Every senior driver has a different routine — and a different risk.
MASIL is designed around those differences.
Our goal is to make senior driving risk more personal, more visible, and more manageable.
That is why we propose MASIL —
 a new insurance rider for an aging society.
Thank you.
