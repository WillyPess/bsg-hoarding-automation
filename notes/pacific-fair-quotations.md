---
name: pacific-fair-quotations
description: Workflow and rate mapping for quoting Pacific Fair (GPT) hoarding jobs from BSG's 25-26 rate card; done in thread "Pacific Fair - Quotations"
metadata:
  type: project
  modified: 2026-11-01T04:49:48.006Z
---

Workflow (Gus, 2026-11-01): the three hoarding threads (Shopfront hoarding drawings, Corner shop hoarding, Hoarding next to fire doors) must ask Gus where each job is. If it is at Pacific Fair, they send the job package (job.json, plan, materials) to the thread "Pacific Fair - Quotations", and Gus gets the quote only from that thread.

Rate card: "BSG Hoarding Rate - Pacific Fair - 25-26" (Titan, 16 mm white melamine, taped joints), effective 18/6/2025 to 30/6/2026, all ex GST, per lineal metre:
1.2 m kiosk $115 | up to 2.4 m $220 | up to 3.6 m $280 | up to 4.2 m $320 | up to 4.8 m $330 | up to 6.0 m $450 | over 6.0 m POA.
Minimums: 15 lm for kiosks, 10 lm for taller hoardings. Included: 1 set of double doors (2340 x 1600, deadbolt by Pacific Fair + barrel bolt), engineering cert, drawing, up to 6 months on site.
Extras: extra double doors $400/set during install, $800 after; passage set $50/set (instead of hasp & staple); post-install modification $800 min (2 men x 4 h, materials extra; $680 for hoardings installed before 1/10/2025), general mod rate $100/h; cancellation $200 after 2 pm, $900 after 5 pm/dispatched, full cost if team onsite. Scissor lift not included over 4.2 m (Pacific Fair supplies EWP). Public holiday surcharge, oversized transport, wind-rated: POA.

Pricing rules (Gus, 2026-11-01): the 25-26 card is still current. Charge lm = the FULL hoarding run (all faces incl. returns), band = smallest height band >= job height, apply the minimum, add extras, then GST 10%. Fire-door track/timber sections cost nothing extra for now (Gus will say if that changes). Quotes are addressed to GPT - Pacific Fair (may change later). No BSG quote template exists, so I made a general one that explains clearly to the customer how the price is worked out, what is included, extras, terms and acceptance.

Tool: /mnt/project-files/hoarding/quotes/quote_gen.py <job.json> [out.pdf] writes <Job>/<prefix>_Quotation.pdf (number PF-<PREFIX>-<yymmdd>, valid 30 days, the job's hoarding sheet attached). Optional job.json keys: quote_no, quote_date, extra_doors, extra_doors_after, passage_sets, kiosk, valid_days.
Medibank (first quote, 2026-11-01): 12.1 lm x $320 = $3,872.00 ex GST, $4,259.20 inc GST.
David Jones Lift Area (2026-11-01, final, Gus chose to leave wind as POA): external U-shaped kiosk hoarding on rooftop car park, 24.6 lm x $220 (2.4 m band, not the kiosk rate) = $5,412 ex GST; wind loading (40% more uprights, 8 weights each) left as a POA line (Gus). Quote overrides kept in DavidJonesLift/quote_extras.json.
David Jones Ground (PF-DAVIDJONES-261101) and First Level (PF-DAVIDJONES1-261101), 2026-11-01: 23.2 lm x $330 (4.5 m) = $7,656 ex GST each. FRED (quote from FRED_v2, not the old FRED folder): 14.2 lm x $330 = $4,686 ex GST, quote_no PF-FRED-261101. Bikini is at Hyperdome, not Pacific Fair.
Related: [[hoarding-job-package]], [[hoarding-fire-door-jobs]], [[hoarding-corner-jobs]].
