# 데이터 분석 방법론 조사 근거

확인일: 2026-11-04. 공개 검색어만 사용했고 아래 원문의 해당 구간을 직접 열어 확인했다. 검색 요약·접근 실패를 원문 확인으로 대신하지 않았다. 외부 절차를 이 하네스의 필수 조직 승인/도구 설치로 이식하지 않는다.

| ID·원문 | 확인한 범위·시점 | 채택/수정·제외 |
|---|---|---|
| S1 [PPDAC, 뉴질랜드 교육부](https://newzealandcurriculum.tahurangi.education.govt.nz/5637219668.p) | Statistical enquiry cycle 정의와5단계·단계별 목적 | 질문에서 근거 있는 결론으로 닫는 가벼운 틀을 참고한다. 교육용 설명을 기업 공통 의무 표준으로 주장하지 않는다. |
| S2 [CRISP-DM 1.0 원본](https://www.kde.cs.uni-kassel.de/wp-content/uploads/lehre/ws2012-13/kdd/files/CRISPWP-0800.pdf) | Chapman 외,2000, 원본 표지/저자·pp.13–14의 반복 수명주기·6단계·보고서도 가능한 활용 범위 | 큰 과제의 목적·자료 이해·준비·평가·활용을 연결한다. 모든 파일 분석에 ML·배포를 강제하지 않는다. 공개 대학 보관본이며 IBM HTML/PDF는403으로 확인 실패했다. |
| S3 [NIST: What is EDA?](https://www.itl.nist.gov/div898/handbook/eda/section1/eda11.htm) | EDA의 목적·구조/이상치/가정 탐색과 요약/그래프의 역할 | 질문별 탐색과 계산/시각 대조를 채택한다. EDA를 그래프 목록이나 모든 자료에 특정 분포를 강제하는 절차로 바꾸지 않는다. |
| S4 [Government Data Quality Framework](https://www.gov.uk/government/publications/the-government-data-quality-framework/the-government-data-quality-framework) | 2020-12-03 문서의6품질 차원·목적별 trade-off·유효/완전함과 현실 정확성의 구분 | 질문에 필요한 품질 측정·오류 건수·분모와 남은 정확성 한계를 기록한다. 보편적인 단일 품질 점수/탈락 임계값은 채택하지 않는다. |
| S5 [Wickham, Tidy Data](https://www.jstatsoft.org/article/view/v059i10/) | 2014-09-12 JSS 원논문 초록의 변수·관측·관측 단위 구분; 본문 전체를 읽은 것으로 주장하지 않음 | CSV/중첩JSON 관측 단위·관계 보존에 적용한다. 모든 원본을 한 표로 펴거나 특정 R 도구를 의무 설치하지 않는다. |
| S6 [AQuA Book](https://www.gov.uk/guidance/the-aqua-book) | 2025-07-30판, 1.3·7·8의 비례적 보증·목적 적합성/구현 검증·분석 코드/자료·불확실성 기록 | 위험과 복잡도에 맞는 확인·재현·한계를 채택한다. 정부 조직의 모든 역할·서명 절차를 로컬 분석의 추가 승인으로 가져오지 않는다. |
| S7 [ASA 공식 p-value 성명 안내](https://www.amstat.org/asa/files/pdfs/p-valuestatement.pdf) | 2016-03-07, p.2의6원칙·구간 등 대안과 투명한 보고 | p-value를 참일 확률/효과 크기로 해석하거나 단일 임계값으로 의사결정하지 않는다. 탐색/확인·실무적 차이·불확실성을 구분한다. |
| S8 [SciPy false_discovery_control](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.false_discovery_control.html) | 조회 시1.18.0 문서, FDR 정의·BH/BY와 의존성 조건 | 여러 비교를 본 사실과 보정의 목적/가정을 확인한다. 특정 보정/라이브러리를 모든 분석의 기본값으로 고정하지 않는다. |
| S9 [scikit-learn Common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html) | 조회 시1.9.1, 12.2의 평가 자료 누출·분리 후 학습 전처리 | 예측이 필요한 경우만 평가 자료를 분리하고 학습 자료에서 전처리를 학습한다. 예측 성능을 인과 효과로 해석하지 않는다. |
| S10 [pandas read_csv](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html) | 조회 시3.1.0, dtype·NA 옵션·chunksize/iterator | 식별자·범주·결측 정책과 전체/청크 범위를 명시한다. dtype만으로 NA 파싱까지 보존된다고 하지 않는다. |
| S11 [pandas json_normalize](https://pandas.pydata.org/docs/reference/api/pandas.json_normalize.html) | 조회 시3.1.0, record_path·meta·오류 정책 | 실제 중첩 경로·부모 키를 확인하고 전개 뒤 관측 단위/총계를 대조한다. 원본 덮어쓰기·무조건 전개를 채택하지 않는다. |

위 도구 문서 버전은 이번에 관측한 버전이며 하네스 지원 버전·의존성 고정을 뜻하지 않는다. 의료 연구의 결측 처리 논문은 검색 후보로 찾았지만 PMC 원문은 브라우저 확인 화면, Europe PMC는 도구 접근 불가였다. 그 논문을 직접 읽거나 특정 결측 메커니즘/대체법을 검증한 것으로 채택하지 않았다.
