# IncuBrix AI Background Music Engine — Automated Test Summary

**Execution Timestamp:** 2026-10-23T14:29:09Z  
**Total Cases:** 15 | **Passed:** 15 | **Failed:** 0  

## Results Table

| Case Name | Status | Elapsed | Cost | LUFS | True Peak | Gates | Warnings & Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `hard_case_01_short_duration_5s` | ✅ PASS | 20.02s | $0.0000 | -16.0 LUFS | -2.85 dBTP | 9/9 | All Must-Have gates verified. |
| `hard_case_02_short_duration_6s` | ✅ PASS | 19.98s | $0.0000 | -16.0 LUFS | -3.64 dBTP | 9/9 | All Must-Have gates verified. |
| `hard_case_03_long_duration_300s` | ✅ PASS | 84.01s | $0.0000 | -16.0 LUFS | -3.56 dBTP | 9/9 | All Must-Have gates verified. |
| `hard_case_04_contradictory_prompt` | ✅ PASS | 20.42s | $0.0000 | -16.0 LUFS | -3.95 dBTP | 9/9 | Confirmed contradictory warning emitted. (Warnings: Contradictory prompt descriptors detected ('calm' and 'aggressive'). Interpreting as dynamic contrast: gradual progression from calm to aggressive.; Contradictory prompt descriptors detected ('relaxing' and 'intense'). Interpreting as dynamic contrast: gradual progression from relaxing to intense.) |
| `hard_case_05_artist_song_reference` | ✅ PASS | 20.36s | $0.0000 | -16.0 LUFS | -3.43 dBTP | 9/9 | Confirmed artist protection warning emitted. (Warnings: Artist reference detected ('taylor swift'). Copyright imitation protection active: transformed to generic acoustic/stylistic descriptors to prevent infringement of existing recordings.; Song title reference detected ('shake it off'). Copyright protection active: the system will not reproduce copyrighted melodic or harmonic sequences.) |
| `hard_case_06_vocal_request` | ✅ PASS | 20.53s | $0.0000 | -16.0 LUFS | -3.51 dBTP | 9/9 | Confirmed vocal suppression warning emitted; output strictly instrumental. (Warnings: Vocal request detected in prompt (vocals, singing, lyrics). IncuBrix engine is strictly instrumental-only for background video music. Vocal synthesis suppressed; rendered as melodic instrumental stems.) |
| `hard_case_07_sections_too_close` | ✅ PASS | 2.09s | -- | -- | -- | -- | Correctly rejected invalid input at request boundary. |
| `hard_case_08_section_after_end` | ✅ PASS | 2.06s | -- | -- | -- | -- | Correctly rejected invalid input at request boundary. |
| `hard_case_09_narration_long_silence` | ✅ PASS | 24.11s | $0.0000 | -16.0 LUFS | -3.28 dBTP | 9/9 | All Must-Have gates verified. |
| `hard_case_10_narration_no_speech` | ✅ PASS | 20.40s | $0.0000 | -16.0 LUFS | -2.99 dBTP | 9/9 | All Must-Have gates verified. |
| `hard_case_11_non_english_prompt` | ✅ PASS | 20.50s | $0.0000 | -16.0 LUFS | -3.51 dBTP | 9/9 | Confirmed non-English prompt normalized without error. (Warnings: Non-English prompt detected (ES). Interpreted musical intent as instrumental video cue without error.) |
| `hard_case_12_unsupported_fields` | ✅ PASS | 2.11s | -- | -- | -- | -- | Correctly rejected invalid input at request boundary. |
| `mandatory_01_standard_30s` | ✅ PASS | 24.27s | $0.0000 | -16.0 LUFS | -3.87 dBTP | 9/9 | All Must-Have gates verified. |
| `mandatory_02_cinematic_45s_sections` | ✅ PASS | 28.13s | $0.0000 | -16.0 LUFS | -2.28 dBTP | 9/9 | All Must-Have gates verified. |
| `mandatory_03_lofi_loopable_20s` | ✅ PASS | 23.68s | $0.0000 | -16.0 LUFS | -3.42 dBTP | 9/9 | All Must-Have gates verified. |
