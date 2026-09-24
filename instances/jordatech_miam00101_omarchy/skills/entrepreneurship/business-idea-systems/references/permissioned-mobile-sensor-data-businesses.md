# Permissioned Mobile-Sensor Dataset Businesses

Session-derived pattern from developing `Common Sense - Dataset Collector`, a business model for AI companies that lack real-world phone-sensor training/evaluation data.

## Reframe risky wording

If the user's raw idea says "phone sensor scraping," reframe externally as:

- permissioned phone-sensor data collection
- opt-in mobile sensing datasets
- consented real-world sensor-data network

Avoid language that implies covert collection, surveillance, or scraping. This business class only works as a trust/compliance product.

## Buyer persona

Start with specific AI data buyers, not "AI companies" broadly:

- Head of Data / Data Acquisition
- ML Dataset Program Manager
- robotics/perception research lead
- multimodal model evaluation lead
- AI product team needing physical-world edge cases

Good beachheads: robotics navigation, embodied AI, AR/VR spatial understanding, audio scene understanding, mobile activity recognition, accessibility AI, inspection AI.

## Product shape

Two-sided network:

1. Buyers post bounded dataset bounties: geography, device cohort, sensor types, scenario/task, volume, quality thresholds, metadata, consent needs, budget.
2. Phone users opt into paid tasks with clear sensor permissions and visible recording/collection indicators.
3. Platform handles consent provenance, device capability profiles, quality checks, fraud detection, normalization, redaction, dataset packaging, and delivery.

## Sensor/privacy sequencing

Do not start with every sensor. Sequence by trust risk:

- Lower-risk v0: IMU/9-axis motion, ambient light, barometer where available, limited GPS for bounded active tasks.
- Higher-risk later: camera, audio, precise location, bystander data, biometric-adjacent data, sensitive places.

Favor task-based active collection over always-on background collection.

## MVBP pattern

A strong MVBP is a manually operated Android-first pilot:

- one reference device cohort
- one non-sensitive sensor package, e.g. IMU + GPS + ambient light
- one geography/community
- one buyer-defined task
- manual participant payment
- manual dataset delivery as CSV/parquet/ZIP plus dataset card
- consent and provenance log

Success criteria:

- 1 paid pilot or signed LOI
- 100+ usable sessions
- under ~20% rejected sessions after quality checks
- participant acquisition cost supports gross margin
- buyer says the dataset is faster/better/cheaper than alternatives

## Phone-platform assumptions to check

For global reach, Android usually wins. In the 2026 session, StatCounter snapshots showed Android with majority mobile OS share worldwide and especially in Africa/Asia/South America. Use current sources when re-running research; do not hard-code old percentages in new outputs without checking.

Practical device recommendation for an MVBP:

- Samsung Galaxy A-series for globally common low/mid-range Android coverage.
- Google Pixel for clean Android reference/development testing.
- iPhone later for premium markets and long support windows when buyer demand requires iOS.

## Platform-agnostic app architecture

Use a cross-platform shell plus native plugins:

- React Native or Flutter for onboarding, consent, task marketplace, payouts, instructions, upload status.
- Android native module: SensorManager, CameraX, MediaRecorder/AudioRecord, Location APIs.
- iOS native module: Core Motion, AVFoundation, Core Location.
- Canonical sensor event schema with session_id, pseudonymous participant_id, device_model, OS, sensor_type, timestamp, sampling_rate, units, values, permission_scope, consent_version.
- Capability detection on install so users only see tasks their device can perform.
- Server-side normalization: timestamp alignment, calibration metadata, missing-data flags, quality scoring, redaction, dataset cards, provenance logs.

## Revenue streams

- Dataset bounty marketplace with 20-40% take-rate.
- Managed collection projects: often easier first sale; hypothesize $25k-$250k+ depending on complexity.
- Subscription buyer portal for feasibility/cohort targeting/recurring workflows.
- Non-exclusive dataset licensing if consent allows.
- Consent/provenance/quality API.

## Trust/compliance risks

Key risk: not enough data points because users do not trust the app. Mitigate with clear consent, immediate payment, task-specific permissions, preview/delete controls where possible, privacy promises, partner channels, and avoiding sensitive sensors in v0.

Other risks: app-store policies, regional privacy laws, audio/video/bystander consent, precise location sensitivity, noisy phone data, device fragmentation, spoofing/fraud, synthetic submissions.

## Lead generation / supply notes

Handshake-style campus channels may be strong for early participant recruitment, ambassadors, QA/data-labeling interns, and controlled campus pilots. Enterprise channels like Mercer only fit if the product is repositioned toward workforce/environment/safety analytics or participant compensation research.

## Customer discovery questions

For AI buyers:

- Tell me about the last dataset your team needed but could not get.
- What exact fields/modalities/geographies/devices did you need?
- What did you try, how long did it take, and what did it cost?
- What made existing datasets unusable?
- What legal/privacy requirements blocked vendors?
- Can you show the dataset spec/request your team used last time?

For participants:

- Tell me about the last app that asked for location, camera, or microphone access.
- What made you trust or not trust it?
- Have you completed paid app tasks, surveys, gigs, or research studies?
- Which permissions are an instant no?
- Would preview/delete before upload change comfort level?
- What payout makes a 5-minute bounded sensor task worth doing?
