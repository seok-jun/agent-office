# 선택 설치: 실시간 압축 신호

일반 작업 상태는 훅 없이 로그에서 읽습니다. 압축 시작과 종료를 즉시 반영하려면 이 가이드를 따르세요.
설치 확인 기준은 Codex CLI 0.165.0, Claude Code 2.1.303입니다. 과거 버전의 호환성은 보장하지 않습니다.

## 설치

앱 폴더를 장기간 사용할 위치에 둔 다음 폴더에서 실행합니다.

```powershell
python install_hooks.py --provider Codex --preview
python install_hooks.py --provider Codex
```

Claude만 쓰면 `--provider Claude`, 둘 다 쓰면 `--provider both`를 사용하세요.
`--preview`는 변경 내용을 보여주기만 합니다. 출력에는 **해당 PC의 로컬 경로**가 있으므로 그대로 게시하지 마세요.

- Codex: `CODEX_HOME/hooks.json` (기본 사용자 홈의 `.codex/hooks.json`)
- Claude: `CLAUDE_CONFIG_DIR/settings.json` (기본 사용자 홈의 `.claude/settings.json`)
- 기존 설정과 다른 훅을 보존하며, 같은 정의를 다시 설치하면 중복 등록하지 않습니다.
- 기존 파일은 앱의 `runtime/backups`에 백업합니다. 전체 설정을 포함하므로 비공개로 보관하세요.
- 설치한 Python과 스크립트의 절대 경로를 **사용자 PC에서 생성**합니다. 저장소에 개인 경로를 배포하지 않습니다.

Codex CLI의 `/hooks`에서 이 앱의 `compaction_hook.py` 실행 항목을 검토하고 신뢰로 설정합니다.
Windows 명령은 공백·한글·특수문자 경로를 안전하게 전달하기 위해 인코딩된 PowerShell 명령을 사용합니다.
실제 동작은 선택한 Python으로 `compaction_hook.py Codex`를 실행하는 것뿐입니다.
신뢰를 자동으로 설정하거나 사용자 승인을 우회하지 않습니다.

기존 Claude/Codex 세션에 새 설정이 반영되지 않으면 재시작 후 기존 세션을 재개하세요.
다른 도구의 승인·질문 응답은 항상 해당 도구에서 처리합니다.

## 확인

1. Agent Office를 일반 모드로 실행합니다.
2. 연결한 도구에서 실제 압축을 실행합니다.
3. 앱의 `안내`에서 공급자별 마지막 신호 수신 시각을 확인합니다.
4. 압축 시작 시 커피로, 종료 시 자기 책상으로 향하는지 확인합니다.

완료 로그만 남는 환경에서는 시작을 추정하지 않습니다. 압축이 짧으면 커피에 도착하기 전에 돌아올 수 있습니다.
커피 자리는 동시에 3개입니다. 질문·승인·오류 상태가 우선합니다.
완료 신호가 유실되면 완료 로그로 복구하며, 아무 종료 증거도 없으면 30분 뒤 압축 표시를 해제합니다.
파일 접근 권한·훅 신뢰·도구 버전에 따라 동작이 달라질 수 있습니다.

## 제거 / 폴더 이동

**폴더를 옮기거나 Python을 변경하기 전에**, 설치했던 Python과 원래 앱 위치에서 실행하세요.

```powershell
python install_hooks.py --provider both --remove --preview
python install_hooks.py --provider both --remove
```

현재 설치가 생성하는 정의와 정확히 같은 훅만 제거합니다. 다른 훅·권한은 보존합니다.
명령을 수동 수정했거나 원래 설치 위치/Python이 바뀌었다면 자동 제거가 해당 항목을 찾지 못할 수 있습니다.
그 경우 설정 파일에서 옛 `compaction_hook.py`를 가리키는 항목만 검토해 제거하세요.
백업 전체를 덮어쓰면 나중에 수정한 다른 설정까지 잃을 수 있으므로 무조건 복원하지 마세요.
폴더 이동 후 새 위치에서 설치하고 Codex 신뢰도 다시 검토합니다.

제거는 백업과 이벤트 파일을 지우지 않습니다. 더 이상 필요 없으면 앱을 닫고 로컬 `runtime` 폴더를 정리할 수 있습니다.

## 공식 참고

- [Codex hooks](https://learn.chatgpt.com/docs/hooks)
- [Claude Code hooks](https://code.claude.com/docs/en/hooks)

훅은 stdin의 JSON에서 식별자와 이벤트만 저장하며 stdout에 승인 결정이나 모델 지시를 반환하지 않습니다.

## macOS 명령

설치 후 `.venv/bin/python install_hooks.py --provider Codex --preview`와
`.venv/bin/python install_hooks.py --provider Codex`를 사용합니다.
Codex의 POSIX 명령은 각 인자를 셸 인용하여 공백·한글·특수문자를 보호합니다.
Claude 명령은 실행 파일과 인자 배열을 별도로 전달합니다.
Codex `/hooks`의 사용자 신뢰 확인과 세션 재시작 절차는 동일합니다.
