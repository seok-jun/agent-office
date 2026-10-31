# Agent Office

Claude Code와 Codex의 로컬 작업 상태를 도트 사무실로 보여주는 독립 데스크톱 앱입니다.
작업 중에는 책상으로, 질문·승인 대기에는 내 자리 앞으로, 압축 중에는 커피 코너로 이동합니다.

GitHub에는 코드만 배포합니다. 시작할 때 **PC에 있는 Codex 펫 이미지를 자동 탐색**하고,
찾지 못한 펫만 로봇으로 표시합니다. 외부 이미지를 배포본에 넣거나 자동 다운로드하지 않습니다.
[이미지 탐색 안내](docs/ASSETS.md)

## 에이전트에게 설치 맡기기

repo 주소와 함께 “AGENTS.md를 따라 내 로컬에 설치하고 Claude/Codex에 연결·진단해 줘”라고 요청하세요.
[에이전트 설치 지침](AGENTS.md) · [통합 설치와 진단 가이드](docs/INSTALL.md)

```powershell
python setup_office.py --dry-run
python setup_office.py
.\.venv\Scripts\python.exe doctor.py --json
```

설치가 끝나면 `Start.cmd`로 실행합니다. Codex 훅 신뢰는 사용자가 `/hooks`에서 직접 확인합니다.
네트워크 없이 준비하려면 `python setup_office.py --robot-only`를 사용하세요.

## 수동 빠른 시작 — Windows

1. Python 3.14와 tkinter를 설치합니다. 개발·실행 확인 환경은 Windows / Python 3.14입니다.
   다른 Python 3 버전과 macOS/Linux는 아직 검증하지 않았습니다.
2. 저장소 ZIP을 내려받아 **압축을 풉니다**. Git을 사용한다면 아래 명령으로 받습니다.

   ```powershell
   git clone https://github.com/seok-jun/agent-office.git
   cd agent-office
   ```

3. `Start.cmd`를 더블 클릭하거나 폴더에서 실행합니다.

   ```powershell
   python app.py
   ```

로봇 모드에는 추가 pip 패키지가 필요하지 않습니다. Codex CLI의 로컬 WebP 펫을 표시하려면 설치하세요.

```powershell
python -m pip install -r requirements.txt
```

API 키나 Agent Office 계정은 필요하지 않습니다.
Claude/Codex 자체의 설치·로그인·이용 조건은 별도입니다. 둘 중 하나만 사용해도 됩니다.

### 연결 없이 둘러보기

```powershell
python app.py --demo
```

가상의 12개 세션만 표시하며 로컬 세션 기록을 읽지 않습니다.
이 모드에서는 실시간 모드로 전환하지 않습니다. 실제 연결은 앱을 닫고 `python app.py`로 실행하세요.
일반 실행 중의 `시연 보기` 버튼은 화면만 전환하며 백그라운드 모니터링은 계속됩니다.

## 실제 세션 연결

평소처럼 Claude Code 또는 Codex에서 작업하면 기록을 자동 탐색합니다.

| 공급자 | 기본 기록 위치 | 사용자 지정 |
| --- | --- | --- |
| Codex | 사용자 홈의 `.codex/sessions` | `CODEX_HOME` 아래 `sessions` |
| Claude | 사용자 홈의 `.claude/projects` | `CLAUDE_CONFIG_DIR` 아래 `projects` |

앱은 같은 컴퓨터에서 접근할 수 있는 기록만 읽습니다. 클라우드·원격·WSL 세션은 자동 연결을 보장하지 않습니다.
환경변수는 해당 도구와 Agent Office에서 같은 루트를 가리키도록 설정한 뒤 앱을 다시 실행하세요.

**압축 시작·종료 실시간 연출은 선택 설치인 [훅 연결 가이드](docs/HOOKS.md)가 필요합니다.**
일반 로그는 3초마다, 압축 훅 신호는 약 0.2초마다 확인합니다. UI 반영에는 추가 지연이 생길 수 있습니다.

## 사무실에서 보이는 것

| 상태 | 연출 |
| --- | --- |
| 작업·생각 | 책상에서 작업, 공개 진행 내용 말풍선 |
| 질문·승인 요청 | 내 자리 앞에 줄 서기, `내 응답 필요` 목록 |
| 컨텍스트 압축 | 커피로 이동 → 압축 중 대기 → 종료 시 책상 복귀 |
| 완료·1시간 비활동 | 소파 휴식과 가끔 커피, 접을 수 있는 대기 목록 |
| 사용량 제한·중단 | 책상에서 잠들기, 확인 가능한 경우 재개 시각 안내 |
| 서브 에이전트 완료 | 확인된 부모에게 보고하는 연출 |

메인 에이전트를 클릭하면 연결된 서브 에이전트를 함께 강조합니다.
Claude가 `codex exec`로 호출한 Codex도 재개 명령의 세션 ID나 실행 결과의 `thread.started` 기록이 확인되면 같은 팀으로 연결합니다.
`--json` 출력을 로컬 JSONL로 돌린 경우, 명령에 명시된 프로젝트·임시·세션 폴더 안 파일의 첫 16 KiB에서 식별자만 확인합니다.
프로젝트 이름이나 호출 시각만으로 관계를 추정하지 않으며, 정확한 식별자가 없는 실행은 독립 세션으로 표시합니다.
최대 12명 표시 안에서 우선 세션의 확인된 부모도 함께 포함합니다.
질문·승인은 원래 Claude/Codex에서 처리해야 합니다. Agent Office는 답변하거나 승인하지 않습니다.

Claude의 Clawd는 헤드셋·안경·후드·베레모 등 12종 옷차림으로 구분됩니다.
같은 세션은 같은 외형을 유지하며, 책상에서 작업·생각할 때는 노트북 타이핑 동작을 보여줍니다.
상단의 `Clawd 옷장`에서 12종의 대기·작업 모습을 확인할 수 있습니다.

## 감지 범위와 개인정보

- 최근 24시간의 최신 기록 최대 48개를 확인하고, 활동·응답 대기 우선으로 최대 12개를 표시합니다.
- 프로세스 실행 여부를 직접 감시하지 않으므로 화면의 캐릭터가 모두 현재 열린 세션인 것은 아닙니다.
- 기록에 명시된 요청과 상태만 감지합니다. 모든 앱 버전의 승인 UI나 내부 압축을 감지한다고 보장하지 않습니다.
- 기록 갱신이 3분 이상 없으면 상태 미확인, 1시간 비활동이면 대기로 표시할 수 있습니다.
- 로컬 파일명·프로젝트명·공개 진행 문구·질문 요약이 화면에 보일 수 있습니다. 공유 화면은 `--demo`를 사용하세요.
- 별도 네트워크 전송·분석 수집·API 호출은 없습니다. 프롬프트나 내부 추론을 표시하도록 설계하지 않았습니다.
- 훅은 세션 ID·기록 경로·이벤트 시각을 `runtime/compaction`에 기록합니다.
  설치 백업은 `runtime/backups`에 있으며 기존 설정 전체가 들어갈 수 있습니다. `runtime`은 공개하지 마세요.

## 문제 해결

- 창이 바로 닫힘: 터미널에서 `python app.py`를 실행해 오류를 확인합니다.
- Python을 찾지 못함: Python 설치와 PATH를 확인하거나 `py -3 app.py`를 사용합니다.
- tkinter 오류: `python -m tkinter`로 확인하고 tkinter가 포함된 Python을 설치합니다.
- 캐릭터 없음: 최근 작업 기록이 있는지와 환경변수 경로를 확인합니다. 처음 설치한 PC에서는 정상일 수 있습니다.
- 압축 시 커피에 안 감: [훅 신뢰·재시작·수신 확인](docs/HOOKS.md)을 확인합니다.
- 말풍선 내용이 다름: 공개 로그의 요약이므로 실제 내부 처리와 시간차·누락이 있을 수 있습니다.
- 펫이 로봇으로 보임: 로컬 이미지가 없거나 읽을 수 없는 경우의 대체 표시입니다. Pillow 설치와 Codex 펫 캐시를 확인하고 앱을 재실행하세요. [자산 안내](docs/ASSETS.md)를 참고하세요.

## 개발과 검증

```powershell
python -m unittest discover -s tests -v
```

`app.py`는 UI, `office.py`는 사무실·캐릭터, `monitor.py`는 로그 해석,
`compaction_hook.py`와 `live_compaction.py`는 로컬 압축 신호를 담당합니다.
테스트는 임시 가상 기록을 사용합니다. 실제 사용자 설정에 설치하는 명령은 별도로 실행해야 합니다.

코드 라이선스는 [MIT](LICENSE)입니다. 외부 캐릭터·브랜드 권리는 이 라이선스에 포함되지 않습니다.
이 프로젝트는 OpenAI 또는 Anthropic의 공식 제품이나 제휴 프로젝트가 아닙니다.

## English quick start

A local desktop pixel office for Claude Code and Codex. Tested on Windows with Python 3.14 and tkinter.
Extract the source folder and run `python app.py`, or `python app.py --demo` for fictional sessions without reading local logs.
No API key is required. Install `requirements.txt` to read local WebP pet sprites; robots work without it. Live compaction uses optional hooks; see [setup](docs/HOOKS.md).
Artwork is not bundled. Existing Codex CLI pet sprites are read locally; missing or unreadable sprites fall back to robots.
Never publish `runtime/`, session transcripts, personal settings, or screenshots of live sessions.
