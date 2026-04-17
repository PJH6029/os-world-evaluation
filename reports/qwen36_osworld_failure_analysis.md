# Qwen3.6 OSWorld Qualitative Failure Analysis

This report is generated from trajectory artifacts. Failure tags are **agent-suggested** unless later manually verified. It is a sampled no-Google-Drive qualitative evaluation, not a full OSWorld leaderboard result.

## Status counts

- Sampled: 50
- Attempted: 50
- success: 8
- model_failure: 41
- environment_invalid: 1
- unknown: 0
- not_run: 0

## Qualitative headline observations

- Successes: 8/50 sampled tasks (8/49 excluding environment-invalid rows).
- Model failures: 41, including 31 runs that ended because no parseable action was produced and 10 evaluated runs with score 0.0.
- Result-backed evaluations: 18; the remaining model-failure rows are still trajectory-backed but ended before OSWorld produced `result.txt`.
- Domain status counts:
  - chrome: model_failure=3, success=2
  - gimp: model_failure=5
  - libreoffice_calc: model_failure=5
  - libreoffice_impress: model_failure=5
  - libreoffice_writer: model_failure=5
  - multi_apps: model_failure=5
  - os: model_failure=4, success=1
  - thunderbird: model_failure=4, success=1
  - vlc: environment_invalid=1, model_failure=2, success=2
  - vs_code: model_failure=3, success=2

## Failure taxonomy coverage

### Bad visual perception

- **chrome/6c4c23a1-42a4-43cc-9db1-2f86ff3738cc** — status `model_failure`, score `0.0`.
  - Instruction: Find flights from Seattle to New York on 5th next month and only show those that can be purchased with miles.
  - Evidence: [traj](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/chrome/6c4c23a1-42a4-43cc-9db1-2f86ff3738cc/traj.jsonl), [initial observation](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/chrome/6c4c23a1-42a4-43cc-9db1-2f86ff3738cc/initial_state.png), [recording](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/chrome/6c4c23a1-42a4-43cc-9db1-2f86ff3738cc/recording.mp4)
  - Suggested tags: action_grounding, planning, tool_ui_confusion, visual_perception (`agent_suggested`)

- **gimp/dbbf4b99-2253-4b10-9274-45f246af2466** — status `model_failure`, score `0.0`.
  - Instruction: Use GIMP only to convert my new RAW image into a JPEG file.
  - Evidence: [traj](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/gimp/dbbf4b99-2253-4b10-9274-45f246af2466/traj.jsonl), [initial observation](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/gimp/dbbf4b99-2253-4b10-9274-45f246af2466/initial_state.png), [recording](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/gimp/dbbf4b99-2253-4b10-9274-45f246af2466/recording.mp4)
  - Suggested tags: action_grounding, planning, tool_ui_confusion, visual_perception (`agent_suggested`)

- **gimp/2a729ded-3296-423d-aec4-7dd55ed5fbb3** — status `model_failure`, score `0.0`.
  - Instruction: Could you make the background of this image transparent for me?
  - Evidence: [traj](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/gimp/2a729ded-3296-423d-aec4-7dd55ed5fbb3/traj.jsonl), [initial observation](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/gimp/2a729ded-3296-423d-aec4-7dd55ed5fbb3/initial_state.png), [recording](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/gimp/2a729ded-3296-423d-aec4-7dd55ed5fbb3/recording.mp4)
  - Suggested tags: action_grounding, planning, tool_ui_confusion, visual_perception (`agent_suggested`)


### Bad action grounding

- **chrome/6c4c23a1-42a4-43cc-9db1-2f86ff3738cc** — status `model_failure`, score `0.0`.
  - Instruction: Find flights from Seattle to New York on 5th next month and only show those that can be purchased with miles.
  - Evidence: [traj](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/chrome/6c4c23a1-42a4-43cc-9db1-2f86ff3738cc/traj.jsonl), [initial observation](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/chrome/6c4c23a1-42a4-43cc-9db1-2f86ff3738cc/initial_state.png), [recording](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/chrome/6c4c23a1-42a4-43cc-9db1-2f86ff3738cc/recording.mp4)
  - Suggested tags: action_grounding, planning, tool_ui_confusion, visual_perception (`agent_suggested`)

- **gimp/dbbf4b99-2253-4b10-9274-45f246af2466** — status `model_failure`, score `0.0`.
  - Instruction: Use GIMP only to convert my new RAW image into a JPEG file.
  - Evidence: [traj](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/gimp/dbbf4b99-2253-4b10-9274-45f246af2466/traj.jsonl), [initial observation](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/gimp/dbbf4b99-2253-4b10-9274-45f246af2466/initial_state.png), [recording](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/gimp/dbbf4b99-2253-4b10-9274-45f246af2466/recording.mp4)
  - Suggested tags: action_grounding, planning, tool_ui_confusion, visual_perception (`agent_suggested`)

- **gimp/2a729ded-3296-423d-aec4-7dd55ed5fbb3** — status `model_failure`, score `0.0`.
  - Instruction: Could you make the background of this image transparent for me?
  - Evidence: [traj](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/gimp/2a729ded-3296-423d-aec4-7dd55ed5fbb3/traj.jsonl), [initial observation](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/gimp/2a729ded-3296-423d-aec4-7dd55ed5fbb3/initial_state.png), [recording](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/gimp/2a729ded-3296-423d-aec4-7dd55ed5fbb3/recording.mp4)
  - Suggested tags: action_grounding, planning, tool_ui_confusion, visual_perception (`agent_suggested`)


### Planning errors

- **chrome/6c4c23a1-42a4-43cc-9db1-2f86ff3738cc** — status `model_failure`, score `0.0`.
  - Instruction: Find flights from Seattle to New York on 5th next month and only show those that can be purchased with miles.
  - Evidence: [traj](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/chrome/6c4c23a1-42a4-43cc-9db1-2f86ff3738cc/traj.jsonl), [initial observation](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/chrome/6c4c23a1-42a4-43cc-9db1-2f86ff3738cc/initial_state.png), [recording](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/chrome/6c4c23a1-42a4-43cc-9db1-2f86ff3738cc/recording.mp4)
  - Suggested tags: action_grounding, planning, tool_ui_confusion, visual_perception (`agent_suggested`)

- **gimp/dbbf4b99-2253-4b10-9274-45f246af2466** — status `model_failure`, score `0.0`.
  - Instruction: Use GIMP only to convert my new RAW image into a JPEG file.
  - Evidence: [traj](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/gimp/dbbf4b99-2253-4b10-9274-45f246af2466/traj.jsonl), [initial observation](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/gimp/dbbf4b99-2253-4b10-9274-45f246af2466/initial_state.png), [recording](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/gimp/dbbf4b99-2253-4b10-9274-45f246af2466/recording.mp4)
  - Suggested tags: action_grounding, planning, tool_ui_confusion, visual_perception (`agent_suggested`)

- **gimp/2a729ded-3296-423d-aec4-7dd55ed5fbb3** — status `model_failure`, score `0.0`.
  - Instruction: Could you make the background of this image transparent for me?
  - Evidence: [traj](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/gimp/2a729ded-3296-423d-aec4-7dd55ed5fbb3/traj.jsonl), [initial observation](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/gimp/2a729ded-3296-423d-aec4-7dd55ed5fbb3/initial_state.png), [recording](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/gimp/2a729ded-3296-423d-aec4-7dd55ed5fbb3/recording.mp4)
  - Suggested tags: action_grounding, planning, tool_ui_confusion, visual_perception (`agent_suggested`)


### Tool/UI confusion

- **chrome/7f52cab9-535c-4835-ac8c-391ee64dc930** — status `model_failure`, score `None`.
  - Instruction: Create a list of drip coffee makers that are on sale and within $25-60 and have a black finish.
  - Evidence: [traj](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/chrome/7f52cab9-535c-4835-ac8c-391ee64dc930/traj.jsonl), [initial observation](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/chrome/7f52cab9-535c-4835-ac8c-391ee64dc930/initial_state.png), [recording](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/chrome/7f52cab9-535c-4835-ac8c-391ee64dc930/recording.mp4)
  - Suggested tags: tool_ui_confusion (`agent_suggested`)

- **chrome/6c4c23a1-42a4-43cc-9db1-2f86ff3738cc** — status `model_failure`, score `0.0`.
  - Instruction: Find flights from Seattle to New York on 5th next month and only show those that can be purchased with miles.
  - Evidence: [traj](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/chrome/6c4c23a1-42a4-43cc-9db1-2f86ff3738cc/traj.jsonl), [initial observation](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/chrome/6c4c23a1-42a4-43cc-9db1-2f86ff3738cc/initial_state.png), [recording](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/chrome/6c4c23a1-42a4-43cc-9db1-2f86ff3738cc/recording.mp4)
  - Suggested tags: action_grounding, planning, tool_ui_confusion, visual_perception (`agent_suggested`)

- **chrome/b7895e80-f4d1-4648-bee0-4eb45a6f1fa8** — status `model_failure`, score `None`.
  - Instruction: Find a Hotel in New York City with lowest price possible for 2 adults next weekend.
  - Evidence: [traj](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/chrome/b7895e80-f4d1-4648-bee0-4eb45a6f1fa8/traj.jsonl), [initial observation](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/chrome/b7895e80-f4d1-4648-bee0-4eb45a6f1fa8/initial_state.png), [recording](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/chrome/b7895e80-f4d1-4648-bee0-4eb45a6f1fa8/recording.mp4)
  - Suggested tags: tool_ui_confusion (`agent_suggested`)


## Mixed or uncertain cases

not observed in this sample

## Environment-invalid and unknown cases

- Environment invalid: 1
- Unknown: 0
- **vlc/efcf0d81-0835-4880-b2fd-d866e8bc2294** — status `environment_invalid`, score `None`.
  - Instruction: Make this part of the video my computer's background picture
  - Evidence: [traj](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/vlc/efcf0d81-0835-4880-b2fd-d866e8bc2294/traj.jsonl), [initial observation](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/vlc/efcf0d81-0835-4880-b2fd-d866e8bc2294/initial_state.png), [recording](runs/qwen36_osworld_seed36035_20260417T112849Z/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/vlc/efcf0d81-0835-4880-b2fd-d866e8bc2294/recording.mp4)
  - Suggested tags: none (`agent_suggested`)


## Suggestions for manual follow-up

1. Inspect action-grounding cases by comparing click coordinates against the referenced screenshots.
2. Inspect visual-perception cases by checking whether the relevant text/icon/state was visible in the observation.
3. For planning/tool-confusion cases, replay the action sequence and decide whether the model misunderstood the task or the app state.
4. Keep environment-invalid and unknown rows out of model-failure counts until manually resolved.