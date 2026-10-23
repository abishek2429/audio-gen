# AI_USE.md — AI Coding Assistant Disclosure

In compliance with the IncuBrix Engineering Assessment guidelines ("Disclose everything... list every AI coding tool you used and for what"), this document records the AI tools, models, and workflows employed during development.

---

## 1. Tool & Model Details

* **AI Coding Assistant:** Google DeepMind Antigravity IDE
* **Core Model:** Gemini 3.8 Flash
* **Date of Use:** October 23, 2026
* **Developer/Candidate Role:** System Architect, Audio Engineer, Test Designer, Code Reviewer

---

## 2. Tasks Performed with AI Assistance

1. **Architecture & Provider Adapters:**
   - Designed the decoupled Provider Adapter interface (`MusicGeneratorInterface`, `StemSeparatorInterface`, `AudioProviderInterface`).
   - Implemented `SoundverseAdapter` and `ElevenLabsAdapter` matching official API contracts.
   - Built `MockProvider` generating distinct procedural instrument tracks (drums, bass, harmony, melody).

2. **DSP Finishing Pipeline:**
   - Implemented 48 kHz polyphase rational resampling (`scipy.signal.resample_poly`).
   - Implemented exact sample-accurate duration alignment with a cosine-decay intentional ending curve.
   - Implemented ITU-R BS.1770-4 loudness normalization (-16.0 LUFS) and 4x oversampled True Peak limiting (<= -1.0 dBTP).
   - Implemented voiceover sidechain ducking with smoothed envelope follower.

3. **Automated Verification Harness & Tests:**
   - Implemented `validate_audio_pack` evaluating all IncuBrix Must-Have criteria and calculating reconstruction Signal-to-Distortion Ratio (SDR).
   - Created comprehensive unit and integration tests with pytest (`test_dsp.py`, `test_mock_provider.py`, `test_validator.py`, `test_provider_adapters.py`, `test_cli.py`).

4. **Documentation & Benchmarks:**
   - Synthesized PoC measurement results, comparison tables, and limitations analysis.

---

## 3. Candidate Code Ownership & Understanding

All generated code, mathematical formulas, DSP algorithms, and tests have been inspected, tested, and validated by the candidate. The candidate is fully prepared to explain, modify, and live-debug any component of this engine during the technical live session.
