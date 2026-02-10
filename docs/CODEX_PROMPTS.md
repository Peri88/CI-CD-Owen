## Codex 복구/운영 프롬프트

아래 프롬프트들은 다른 환경에서 이 레포를 복구/운영할 때 Codex에 그대로 전달해 쓰는 용도입니다.

### 1) 레포 복구 + 실행 환경 세팅

```
github.com:Peri88/CI-CD-Owen.git 레포를 /root/workspace/my-codex-repo에 클론하고,
scripts/byeoksan_watch 기준으로 실행 환경을 세팅해줘.
필요한 경로(/home/owen/...), 템플릿 파일, OneDrive 경로가 없으면 어떤 값을 넣어야 하는지 먼저 물어봐줘.
```

### 2) 감시 스크립트 등록/실행

```
scripts/byeoksan_watch/watch_export1.sh가 자동 감시로 돌도록 실행해줘.
WSL에서 Windows 업로드 이벤트가 누락될 수 있으니 현재 폴링 방식 그대로 유지해줘.
```

### 3) 테스트로 결과 생성

```
/home/owen/Export1.xlsx를 기준으로 결과 파일을 1회 생성해줘.
생성된 결과 파일 경로와 로그를 같이 알려줘.
```

### 4) Git 설정까지 포함한 전체 복구 (한 번에)

```
github.com:Peri88/CI-CD-Owen.git 레포를 /root/workspace/my-codex-repo에 클론해줘.
scripts/byeoksan_watch의 스크립트를 기준으로 실행 환경을 구성하고,
/home/owen 경로, 템플릿 파일, OneDrive 경로가 없으면 필요한 값을 먼저 물어봐줘.
그리고 감시 스크립트를 백그라운드로 실행해서 Export1.xlsx 업로드 시 자동 생성되게 해줘.
마지막으로 테스트로 1회 생성하고 로그를 보여줘.
```
