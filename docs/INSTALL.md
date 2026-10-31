# 에이전트에게 설치 맡기기

아래처럼 요청할 수 있습니다.

> https://github.com/seok-jun/agent-office 를 내 로컬에 설치하고 내가 쓰는 Claude Code/Codex에 연결해 줘.
> AGENTS.md를 따라 기존 설정을 보존하고, 진단까지 해 줘.

저장소를 내려받은 뒤 아래 절차로 설치합니다.

## 통합 설치

Python 3.14와 tkinter를 준비하고 저장소 폴더에서 실행합니다.

```powershell
python setup_office.py --dry-run
python setup_office.py
```

순서: Python/tkinter 확인 → `.venv` 생성/재사용 → Pillow 설치 → 설정 형식 점검 → 훅 등록 → 진단.
Pillow는 pip에 설정된 패키지 저장소에서 받습니다. 시스템 Python의 패키지는 변경하지 않습니다.
훅은 가상환경 Python을 가리킵니다. `Start.cmd`도 같은 가상환경을 우선합니다.

| 옵션 | 동작 |
| --- | --- |
| `--dry-run` | 예정 작업만 출력, 파일·설정·네트워크 변경 없음 |
| `--provider auto` | 기본값. 설정 폴더 또는 PATH에서 감지한 공급자 연결 |
| `--provider Claude` / `Codex` / `both` | 연결 대상을 명시 |
| `--provider none` | 훅 설치 없이 앱 환경만 준비 |
| `--robot-only` | Pillow 다운로드 생략. WebP 지원이 없으면 로봇 사용 |

자동 감지는 로그인 여부나 실행 중인 세션을 확인하지 않습니다. 선택한 공급자의 설정 파일이 없으면 새로 만듭니다.
기존 설정 백업은 runtime/backups에 남깁니다. 유효하지 않은 설정은 덮어쓰지 않고 오류로 중단합니다.
중간 실패 시 일부 공급자 설치만 끝났을 수 있습니다. 원인을 해결하고 같은 명령을 다시 실행하세요.

설치 뒤 `Start.cmd`로 실행합니다. Codex 사용자는 `/hooks`에서 이 설치의 훅을 직접 검토·신뢰해야 합니다.
자동 신뢰 처리나 승인 우회는 하지 않습니다. 기존 세션은 필요할 때 재시작해 주세요.

## 연결 진단

```powershell
.\.venv\Scripts\python.exe doctor.py
.\.venv\Scripts\python.exe doctor.py --provider both --json
```

설치 때 선택한 `--provider`를 진단에도 사용하세요. JSON은 에이전트가 읽기 쉬운 구조입니다.
`ok`: 해당 검사 충족, `warning`: 미설치/미수신 등 확인 필요, `manual`: 사용자 확인 필요, `error`: 환경/설정 오류.
종료 코드는 error가 있으면 1, 없으면 0입니다. **0이 모든 연결 완료를 뜻하지는 않습니다.**

Python, 가상환경, tkinter, Pillow, 로그 폴더, 훅 정의 일치, 마지막 로컬 신호, 펫 후보 파일을 확인합니다.
진단은 설정을 변경하지 않고 모델/API를 호출하지 않습니다. 세션 내용이나 전체 개인 경로를 출력하지 않습니다.
로그 폴더 존재는 최근 작업 유무를 보장하지 않으며, 이미지 후보 존재는 정상 디코딩을 보장하지 않습니다.
신뢰 상태는 자동 판정하지 않습니다. 압축 전 신호가 없는 것은 정상일 수 있습니다.
실제 압축 뒤 수신 시각과 앱 움직임까지 확인해야 실제 연결을 확인할 수 있습니다.

## 업데이트와 제거

기존 위치에서 사용자 수정 사항을 보존해 업데이트하고 `python setup_office.py`를 다시 실행합니다.
다른 폴더로 이동하거나 Python을 교체하기 전에는 원래 가상환경에서 제거합니다.

```powershell
.\.venv\Scripts\python.exe install_hooks.py --provider both --remove --preview
.\.venv\Scripts\python.exe install_hooks.py --provider both --remove
```

그 뒤 새 위치에서 설치하세요. 자세한 백업·신뢰·제거 규칙은 [HOOKS.md](HOOKS.md)에 있습니다.

## macOS 설치·진단·제거

Python 3.10+와 tkinter를 준비한 뒤 실행합니다. `python3 -m tkinter`로 GUI 환경을 확인하세요.

```sh
python3 setup_office.py --dry-run
python3 setup_office.py
.venv/bin/python doctor.py --json
sh Start.command
```

Finder 더블 클릭용 실행 권한이 없으면 `chmod +x Start.command`를 한 번 실행하세요.
공급자 옵션과 훅 신뢰 절차는 Windows와 같습니다. 사용자 지정 환경변수가 필요하면 터미널에서 실행합니다.
업데이트는 같은 폴더에서 `python3 setup_office.py`로 진행합니다. 이동·제거 전에는 다음을 실행하세요.

```sh
.venv/bin/python install_hooks.py --provider both --remove --preview
.venv/bin/python install_hooks.py --provider both --remove
```
