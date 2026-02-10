# 벽산 리포트 자동 생성 - 구조와 작동 원리

이 문서는 이 레포에 있는 "벽산 리포트 자동 생성" 스크립트들의 역할과 흐름을 정리합니다.

**요약**
- 엑셀 리포트 생성: `Export1.xlsx`를 파싱해서 `벽산 리포트_백업상태_최종(양식)_YYYYMMDD.xlsx`를 생성/갱신
- PDF 리포트 생성: NetBackup 텍스트 Export를 PDF 템플릿에 채워 `NetBackup_Report_YYYYMMDD_HHMMSS.pdf` 생성
- 자동 실행: `Export1.xlsx` 변경 감지 시 자동 실행 가능

---

## 1) 엑셀 리포트 생성 파이프라인

**입력**
- `/home/owen/Export1.xlsx` (NetBackup Export1 엑셀)
- `/home/owen/벽산 리포트_백업상태_최종(양식).xlsx` (기본 템플릿)

**출력**
- `/home/owen/Export(가공)_YYYYMMDD.xlsx` (가공된 Export1)
- `/home/owen/벽산 리포트_백업상태_최종(양식)_YYYYMMDD.xlsx` (최종 리포트)
- Windows 경로 복사본: `/mnt/c/Users/goust/OneDrive/바탕 화면/22/OneDrive/owen_잡/4. 벽산/`

**흐름**
1. `scripts/run_from_export1.sh` 실행
2. 템플릿 복사 후 날짜가 포함된 리포트 파일 생성
3. `scripts/export1_to_report.py`가 `Export1.xlsx`를 파싱
4. 리포트 시트 `백업상태 점검_일일점검`을 업데이트
5. 결과 리포트를 Windows 경로로 복사

**핵심 스크립트**
- `scripts/run_from_export1.sh`
  - 가상환경 생성/활성화
  - 템플릿 복사
  - `export1_to_report.py` 실행
  - 결과 파일을 Windows 경로로 복사
- `scripts/export1_to_report.py`
  - `Export1.xlsx`에서 정책별 최신 일자의 백업 용량 합산
  - `HZDB_MSSQL` 정책을 인스턴스 기준으로 분리
  - 이전 리포트를 찾아 10GB 이상 증감 시 비고 업데이트

**주의 포인트**
- 경로가 하드코딩 되어 있음(`/home/owen`, Windows OneDrive 경로)
- 리포트 템플릿 파일명이 정확해야 함
- 표지 시트의 날짜는 생성일 기준으로 자동 갱신됨

---

## 2) PDF 리포트 생성 파이프라인

**입력**
- NetBackup Export 텍스트 파일 (예: `/path/to/Export1.txt`)
- 템플릿 PDF: `/home/owen/[벽산] Veritas 백업상태 점검보고서_2026_1월_5주차.pdf`

**출력**
- `/home/owen/NetBackup_Report_YYYYMMDD_HHMMSS.pdf`

**흐름**
1. `scripts/run_report.sh /path/to/Export1.txt` 실행
2. `scripts/nbu_txt_to_pdf.py`가 텍스트를 파싱
3. 템플릿 PDF 레이아웃을 읽어 같은 위치에 값 채움

**핵심 스크립트**
- `scripts/run_report.sh`
  - 가상환경 생성/활성화
  - `nbu_txt_to_pdf.py` 실행
- `scripts/nbu_txt_to_pdf.py`
  - NetBackup 텍스트의 고정폭 컬럼을 파싱
  - 정책/인스턴스 매핑(`POLICY_ROWS`)에 따라 값 배치
  - 템플릿 PDF를 기반으로 ReportLab로 출력 PDF 생성

**주의 포인트**
- `pdftotext`, `pdftoppm` 등 외부 툴 의존성 필요
- 폰트 경로가 하드코딩 되어 있음(`/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf`)

---

## 3) 자동 실행 감시

- `scripts/watch_export1.sh`
  - `/home/owen/Export1.xlsx`의 변경 이벤트를 감시
  - 변경 감지 시 `run_from_export1.sh` 실행
  - 로그는 `/home/owen/export1_watch.log`
  - 실패 시 로그를 Windows 경로로 복사

---

## 4) 품질 확인(선택)

- `scripts/auto_compare.sh`
  - PDF 두 개를 렌더링 후 이미지 비교
  - 결과는 `/tmp/pdfdiff`에 저장

---

## 실행 예시

엑셀 리포트 생성:
```bash
bash /root/workspace/my-codex-repo/scripts/run_from_export1.sh
```

PDF 리포트 생성:
```bash
bash /root/workspace/my-codex-repo/scripts/run_report.sh /path/to/Export1.txt
```

Export1.xlsx 자동 감시:
```bash
bash /root/workspace/my-codex-repo/scripts/watch_export1.sh
```
