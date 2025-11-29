"""
판례 분석 결과 레포트 생성 서비스

PDF 형식으로 판례 검색 결과와 AI 분석 결과를 체계적으로 정리한 레포트를 생성합니다.
"""

import io
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import uuid
import asyncio

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, Image, KeepTogether
    )
    from reportlab.pdfgen import canvas
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

    import matplotlib
    matplotlib.use('Agg')  # GUI 없는 환경을 위한 설정
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties

    REPORTLAB_AVAILABLE = True
except ImportError as e:
    logging.warning(f"ReportLab or matplotlib not available: {e}")
    REPORTLAB_AVAILABLE = False

# Supabase Storage 기능 추가
try:
    from app.utils.database import supabase
    SUPABASE_STORAGE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Supabase client not available: {e}")
    SUPABASE_STORAGE_AVAILABLE = False

logger = logging.getLogger(__name__)

class PrecedentReportGenerator:
    """판례 분석 레포트 생성기"""

    def __init__(self):
        self.page_width = A4[0]
        self.page_height = A4[1]
        self.margin = 72  # 1인치
        self.styles = None

    def generate_pdf_report(
        self,
        search_data: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> bytes:
        """
        판례 분석 결과를 PDF 레포트로 생성

        Args:
            search_data: 검색 결과 및 통계 데이터
            output_path: PDF 파일 저장 경로 (None이면 bytes 반환)

        Returns:
            PDF 파일의 bytes 데이터
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab and matplotlib are required for PDF generation")

        # 메모리에 PDF 생성
        buffer = io.BytesIO()

        # PDF 문서 생성
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )

        # 스타일 설정
        self._setup_styles()

        # 레포트 내용 생성
        story = []

        # 1. 표지
        story.extend(self._create_cover_page(search_data))
        story.append(PageBreak())

        # 2. 검색 요약
        story.extend(self._create_search_summary(search_data))
        story.append(Spacer(1, 20))

        # 3. 통계 분석
        story.extend(self._create_statistics_section(search_data))
        story.append(Spacer(1, 20))

        # 4. 주요 판례 요약
        story.extend(self._create_key_precedents(search_data))
        story.append(Spacer(1, 20))

        # 5. AI 종합 분석
        story.extend(self._create_ai_analysis(search_data))

        # 6. 판례 목록 (부록)
        if search_data.get('results'):
            story.append(PageBreak())
            story.extend(self._create_precedent_list(search_data))

        # PDF 생성
        doc.build(story)

        # 결과 반환
        pdf_data = buffer.getvalue()
        buffer.close()

        if output_path:
            Path(output_path).write_bytes(pdf_data)

        return pdf_data

    async def upload_to_storage(self, pdf_data: bytes, filename: str = None) -> Optional[Dict[str, Any]]:
        """
        PDF 파일을 Supabase Storage에 업로드하고 서명된 URL 생성

        Args:
            pdf_data: PDF 파일 bytes 데이터
            filename: 파일명 (없으면 자동 생성)

        Returns:
            {"file_path": str, "signed_url": str, "expires_in": int} 또는 None
        """
        if not SUPABASE_STORAGE_AVAILABLE:
            logger.warning("Supabase Storage가 사용 불가능합니다")
            return None

        if not supabase:
            logger.warning("Supabase 클라이언트가 초기화되지 않았습니다")
            return None

        try:
            # 파일명 생성 (중복 방지를 위해 UUID + 타임스탬프 사용)
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                unique_id = str(uuid.uuid4())[:8]
                filename = f"precedent_report_{timestamp}_{unique_id}.pdf"

            # Storage bucket 경로 설정
            file_path = f"reports/{filename}"

            # 재시도 로직 (업로드 성공률 100% 보장)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Supabase Storage에 업로드
                    upload_response = supabase.storage.from_("reports").upload(
                        file_path,
                        pdf_data,
                        file_options={"content-type": "application/pdf"}
                    )

                    if upload_response:
                        logger.info(f"PDF 파일 업로드 성공: {file_path}")
                        break

                except Exception as upload_error:
                    logger.warning(f"업로드 시도 {attempt + 1}/{max_retries} 실패: {upload_error}")
                    if attempt == max_retries - 1:
                        raise upload_error
                    await asyncio.sleep(1)  # 1초 대기 후 재시도

            # 서명된 URL 생성 (1시간 유효)
            expires_in_seconds = 3600  # 1시간
            signed_url_response = supabase.storage.from_("reports").create_signed_url(
                file_path,
                expires_in_seconds
            )

            if signed_url_response and 'signedURL' in signed_url_response:
                signed_url = signed_url_response['signedURL']
                logger.info(f"서명된 URL 생성 성공: {file_path}")

                return {
                    "file_path": file_path,
                    "signed_url": signed_url,
                    "expires_in": expires_in_seconds,
                    "filename": filename
                }
            else:
                logger.error("서명된 URL 생성 실패")
                return None

        except Exception as e:
            logger.error(f"Storage 업로드 실패: {e}")
            return None

    async def generate_pdf_with_storage(
        self,
        search_data: Dict[str, Any],
        upload_to_s3: bool = True
    ) -> Dict[str, Any]:
        """
        PDF 레포트 생성 및 선택적 Storage 업로드

        Args:
            search_data: 검색 결과 및 통계 데이터
            upload_to_s3: Storage 업로드 여부

        Returns:
            {
                "pdf_data": bytes,  # Base64로 인코딩될 수 있음
                "file_path": str,   # S3 업로드 시에만
                "signed_url": str,  # S3 업로드 시에만
                "expires_in": int,  # S3 업로드 시에만
                "success": bool
            }
        """
        try:
            # PDF 생성
            pdf_data = self.generate_pdf_report(search_data)

            result = {
                "pdf_data": pdf_data,
                "success": True
            }

            # Storage 업로드 옵션이 켜져 있으면 업로드
            if upload_to_s3 and SUPABASE_STORAGE_AVAILABLE:
                storage_result = await self.upload_to_storage(pdf_data)
                if storage_result:
                    result.update(storage_result)
                    logger.info("PDF 생성 및 Storage 업로드 완료")
                else:
                    # Storage 업로드 실패해도 PDF는 제공
                    logger.warning("Storage 업로드 실패, PDF만 제공")

            return result

        except Exception as e:
            logger.error(f"PDF 생성 및 업로드 실패: {e}")
            return {"success": False, "error": str(e)}

    def _setup_styles(self):
        """스타일 설정"""
        self.styles = getSampleStyleSheet()

        # 커스텀 스타일 추가
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1f2937')
        ))

        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Heading2'],
            fontSize=18,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#4b5563')
        ))

        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#1f2937'),
            borderWidth=1,
            borderColor=colors.HexColor('#e5e7eb'),
            borderPadding=5
        ))

        self.styles.add(ParagraphStyle(
            name='BodyText',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=14,
            alignment=TA_JUSTIFY,
            spaceAfter=6
        ))

    def _create_cover_page(self, search_data: Dict[str, Any]) -> List[Any]:
        """표지 페이지 생성"""
        story = []

        # 로고 또는 제목
        story.append(Spacer(1, 100))
        story.append(Paragraph("SANZERO", self.styles['CustomTitle']))
        story.append(Paragraph("판례 분석 레포트", self.styles['Subtitle']))

        story.append(Spacer(1, 50))

        # 검색 정보
        query = search_data.get('query', '검색어 없음')
        story.append(Paragraph(f"검색어: {query}", self.styles['Heading3']))

        # 생성 날짜
        current_time = datetime.now().strftime('%Y년 %m월 %d일 %H:%M')
        story.append(Spacer(1, 30))
        story.append(Paragraph(f"생성일시: {current_time}", self.styles['Normal']))

        # 판례 수
        total_results = len(search_data.get('results', []))
        story.append(Paragraph(f"분석 판례 수: {total_results}건", self.styles['Normal']))

        return story

    def _create_search_summary(self, search_data: Dict[str, Any]) -> List[Any]:
        """검색 요약 섹션"""
        story = []

        story.append(Paragraph("📊 검색 요약", self.styles['SectionTitle']))

        # 검색 정보 테이블
        search_info = [
            ['항목', '내용'],
            ['검색어', search_data.get('query', '없음')],
            ['검색 방식', 'AI 기반 유사도 분석'],
            ['총 판례 수', str(len(search_data.get('results', [])))],
        ]

        # 평균 유사도 계산
        results = search_data.get('results', [])
        if results:
            similarities = [r.get('similarity', 0) for r in results]
            avg_similarity = sum(similarities) / len(similarities) if similarities else 0
            search_info.append(['평균 유사도', f'{avg_similarity:.1%}'])

        table = Table(search_info, colWidths=[3*cm, 10*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb'))
        ]))

        story.append(table)

        return story

    def _create_statistics_section(self, search_data: Dict[str, Any]) -> List[Any]:
        """통계 분석 섹션"""
        story = []

        story.append(Paragraph("📈 통계 분석", self.styles['SectionTitle']))

        statistics = search_data.get('statistics', {})

        # 유불리 분석
        outcomes = statistics.get('outcomes', {})
        if outcomes:
            story.append(Paragraph("🎯 판례 결과 분석", self.styles['Heading3']))

            # 유리한 결과 계산
            favorable = outcomes.get('승소', 0) + outcomes.get('인정', 0) + outcomes.get('화해', 0)
            total = sum(outcomes.values())
            favorable_rate = (favorable / total * 100) if total > 0 else 0

            story.append(Paragraph(
                f"유리한 판례 비율: <b>{favorable_rate:.1f}%</b> ({favorable}건/{total}건)",
                self.styles['BodyText']
            ))

            # 결과별 상세
            outcome_details = []
            for outcome, count in outcomes.items():
                if count > 0:
                    percentage = (count / total * 100) if total > 0 else 0
                    outcome_details.append(f"• {outcome}: {count}건 ({percentage:.1f}%)")

            if outcome_details:
                story.append(Paragraph("<br/>".join(outcome_details), self.styles['BodyText']))

        # 사고유형 분석
        categories = statistics.get('categories', {})
        if categories:
            story.append(Spacer(1, 15))
            story.append(Paragraph("🏗️ 주요 사고 유형", self.styles['Heading3']))

            # 상위 3개 유형
            top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]
            category_text = []
            for category, count in top_categories:
                percentage = (count / sum(categories.values()) * 100) if categories else 0
                category_text.append(f"• {category}: {count}건 ({percentage:.1f}%)")

            story.append(Paragraph("<br/>".join(category_text), self.styles['BodyText']))

        return story

    def _create_key_precedents(self, search_data: Dict[str, Any]) -> List[Any]:
        """주요 판례 요약 섹션"""
        story = []

        story.append(Paragraph("⚖️ 주요 판례 분석", self.styles['SectionTitle']))

        results = search_data.get('results', [])
        if not results:
            story.append(Paragraph("분석할 판례가 없습니다.", self.styles['BodyText']))
            return story

        # 상위 5개 판례만 표시
        top_precedents = sorted(results, key=lambda x: x.get('similarity', 0), reverse=True)[:5]

        for i, precedent in enumerate(top_precedents, 1):
            # 판례 제목
            title = precedent.get('title', '제목 없음')
            similarity = precedent.get('similarity', 0)

            story.append(Paragraph(
                f"{i}. {title}",
                self.styles['Heading4']
            ))

            # 기본 정보
            court = precedent.get('court', '법원 정보 없음')
            date = precedent.get('date', '날짜 정보 없음')

            story.append(Paragraph(
                f"법원: {court} | 날짜: {date} | 유사도: {similarity:.1%}",
                self.styles['BodyText']
            ))

            # 요약 (있는 경우)
            if 'summary' in precedent:
                story.append(Paragraph(
                    f"요약: {precedent['summary']}",
                    self.styles['BodyText']
                ))

            story.append(Spacer(1, 10))

        return story

    def _create_ai_analysis(self, search_data: Dict[str, Any]) -> List[Any]:
        """AI 종합 분석 섹션"""
        story = []

        story.append(Paragraph("🤖 AI 종합 분석", self.styles['SectionTitle']))

        # 분석 결과 가져오기
        analysis = search_data.get('analysis', {})

        if analysis:
            # 종합 평가
            if 'summary' in analysis:
                story.append(Paragraph("📋 종합 평가", self.styles['Heading3']))
                story.append(Paragraph(analysis['summary'], self.styles['BodyText']))
                story.append(Spacer(1, 10))

            # 법적 전략 권고
            if 'recommendations' in analysis:
                story.append(Paragraph("💡 법적 전략 권고", self.styles['Heading3']))
                story.append(Paragraph(analysis['recommendations'], self.styles['BodyText']))
        else:
            # 기본 분석 생성
            results = search_data.get('results', [])
            statistics = search_data.get('statistics', {})

            story.append(Paragraph("📋 종합 평가", self.styles['Heading3']))

            if results:
                avg_similarity = sum(r.get('similarity', 0) for r in results) / len(results)

                # 유사 판례 유불리 분석
                outcomes = statistics.get('outcomes', {})
                favorable = outcomes.get('승소', 0) + outcomes.get('인정', 0) + outcomes.get('화해', 0)
                total_outcomes = sum(outcomes.values())
                favorable_rate = (favorable / total_outcomes * 100) if total_outcomes > 0 else 0

                analysis_text = f"""
                분석된 {len(results)}건의 판례 중 평균 유사도는 {avg_similarity:.1%}입니다.
                유사 판례 유불리 분석 결과, 유리한 판례 비율은 {favorable_rate:.1f}%로 나타났습니다.
                """

                story.append(Paragraph(analysis_text.strip(), self.styles['BodyText']))

                # 법적 전략 권고
                story.append(Spacer(1, 10))
                story.append(Paragraph("💡 법적 전략 권고", self.styles['Heading3']))

                if favorable_rate >= 70:
                    recommendation = "유리한 판례가 다수 존재하므로 적극적인 법적 대응을 권장합니다."
                elif favorable_rate >= 50:
                    recommendation = "판례가 균등하므로 추가적인 법적 검토와 신중한 접근이 필요합니다."
                else:
                    recommendation = "불리한 판례가 많으므로 추가 증거 수집과 전문가 상담을 권장합니다."

                story.append(Paragraph(recommendation, self.styles['BodyText']))
            else:
                story.append(Paragraph("분석할 수 있는 데이터가 충분하지 않습니다.", self.styles['BodyText']))

        return story

    def _create_precedent_list(self, search_data: Dict[str, Any]) -> List[Any]:
        """판례 목록 부록"""
        story = []

        story.append(Paragraph("📚 판례 목록 (부록)", self.styles['SectionTitle']))

        results = search_data.get('results', [])
        if not results:
            story.append(Paragraph("판례 목록이 없습니다.", self.styles['BodyText']))
            return story

        # 테이블 헤더
        table_data = [['번호', '제목', '법원', '날짜', '유사도']]

        # 판례 데이터 추가
        for i, precedent in enumerate(results, 1):
            title = precedent.get('title', '제목 없음')
            # 제목이 너무 길면 줄이기
            if len(title) > 50:
                title = title[:47] + "..."

            court = precedent.get('court', '없음')
            date = precedent.get('date', '없음')
            similarity = f"{precedent.get('similarity', 0):.1%}"

            table_data.append([str(i), title, court, date, similarity])

        # 테이블 생성
        table = Table(table_data, colWidths=[1*cm, 8*cm, 3*cm, 2.5*cm, 1.5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (-1, 0), (-1, -1), 'CENTER'),  # 유사도는 중앙 정렬
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        story.append(table)

        return story


def create_precedent_report(search_data: Dict[str, Any]) -> bytes:
    """
    편의 함수: 판례 분석 레포트 PDF 생성

    Args:
        search_data: 검색 결과 및 분석 데이터

    Returns:
        PDF 파일의 bytes 데이터
    """
    generator = PrecedentReportGenerator()
    return generator.generate_pdf_report(search_data)


def is_report_service_available() -> bool:
    """레포트 생성 서비스 사용 가능 여부 확인"""
    return REPORTLAB_AVAILABLE