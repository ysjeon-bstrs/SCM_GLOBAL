import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Optional

def plot_step_chart(
    timeline_df: pd.DataFrame,
    start_dt: pd.Timestamp,
    end_dt: pd.Timestamp,
    today: Optional[pd.Timestamp] = None,
    show_wip: bool = True,
    show_transit: bool = True
) -> None:
    """
    계단식 재고 흐름 차트를 그립니다.
    
    Args:
        timeline_df: 타임라인 DataFrame
        start_dt: 시작 날짜
        end_dt: 종료 날짜
        today: 오늘 날짜
        show_wip: WIP 라인 표시 여부
        show_transit: In-Transit 라인 표시 여부
    """
    if timeline_df.empty:
        st.info("차트를 그릴 데이터가 없습니다.")
        return
    
    if today is None:
        today = pd.Timestamp.today().normalize()
    
    # 데이터 필터링
    vis_df = timeline_df[
        (timeline_df["date"] >= start_dt) & 
        (timeline_df["date"] <= end_dt)
    ].copy()
    
    if vis_df.empty:
        st.info("선택된 기간에 데이터가 없습니다.")
        return
    
    # 차트 생성
    fig = go.Figure()
    
    # 센터별 라인 (실선)
    centers = vis_df[vis_df["center"] != "In-Transit"]["center"].unique()
    colors = px.colors.qualitative.Set1
    
    for i, center in enumerate(centers):
        center_data = vis_df[vis_df["center"] == center]
        if not center_data.empty:
            fig.add_trace(go.Scatter(
                x=center_data["date"],
                y=center_data["stock_qty"],
                mode='lines+markers',
                name=center,
                line=dict(width=3),
                marker=dict(size=6),
                hovertemplate=f'<b>{center}</b><br>' +
                             '날짜: %{x}<br>' +
                             '재고: %{y:,}<br>' +
                             '<extra></extra>'
            ))
    
    # In-Transit 라인 (점선)
    if show_transit:
        transit_data = vis_df[vis_df["center"] == "In-Transit"]
        if not transit_data.empty:
            fig.add_trace(go.Scatter(
                x=transit_data["date"],
                y=transit_data["stock_qty"],
                mode='lines+markers',
                name="In-Transit",
                line=dict(dash='dash', width=2),
                marker=dict(size=4),
                hovertemplate='<b>In-Transit</b><br>' +
                             '날짜: %{x}<br>' +
                             '재고: %{y:,}<br>' +
                             '<extra></extra>'
            ))
    
    # 오늘 라인 추가
    fig.add_vline(
        x=today,
        line_dash="dot",
        line_color="red",
        annotation_text="오늘",
        annotation_position="top"
    )
    
    # 레이아웃 설정
    fig.update_layout(
        title="재고 흐름 타임라인",
        xaxis_title="날짜",
        yaxis_title="재고 수량",
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=500,
        showlegend=True
    )
    
    # Y축 포맷
    fig.update_yaxis(tickformat=",")
    
    # 차트 표시
    st.plotly_chart(fig, use_container_width=True)

def plot_inventory_distribution(
    snap_long: pd.DataFrame,
    centers_sel: List[str],
    skus_sel: List[str],
    latest_dt: pd.Timestamp
) -> None:
    """
    재고 분포 차트를 그립니다.
    
    Args:
        snap_long: 정규화된 스냅샷 데이터
        centers_sel: 선택된 센터 목록
        skus_sel: 선택된 SKU 목록
        latest_dt: 최신 날짜
    """
    # 데이터 필터링
    data = snap_long[
        (snap_long["date"] == latest_dt) &
        (snap_long["center"].isin(centers_sel)) &
        (snap_long["resource_code"].isin(skus_sel))
    ].copy()
    
    if data.empty:
        st.info("차트를 그릴 데이터가 없습니다.")
        return
    
    # 센터별 재고 집계
    center_stock = data.groupby("center")["stock_qty"].sum().reset_index()
    
    # 파이 차트
    fig = px.pie(
        center_stock,
        values="stock_qty",
        names="center",
        title="센터별 재고 분포"
    )
    
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>' +
                     '재고: %{value:,}<br>' +
                     '비율: %{percent}<br>' +
                     '<extra></extra>'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def plot_sku_trend(
    timeline_df: pd.DataFrame,
    sku: str,
    start_dt: pd.Timestamp,
    end_dt: pd.Timestamp
) -> None:
    """
    특정 SKU의 재고 추이 차트를 그립니다.
    
    Args:
        timeline_df: 타임라인 DataFrame
        sku: SKU 코드
        start_dt: 시작 날짜
        end_dt: 종료 날짜
    """
    # SKU 데이터 필터링
    sku_data = timeline_df[
        (timeline_df["resource_code"] == sku) &
        (timeline_df["date"] >= start_dt) &
        (timeline_df["date"] <= end_dt)
    ].copy()
    
    if sku_data.empty:
        st.info(f"SKU '{sku}'에 대한 데이터가 없습니다.")
        return
    
    # 차트 생성
    fig = go.Figure()
    
    # 센터별 라인
    centers = sku_data["center"].unique()
    
    for center in centers:
        center_data = sku_data[sku_data["center"] == center]
        if not center_data.empty:
            line_style = 'dash' if center == "In-Transit" else 'solid'
            line_width = 2 if center == "In-Transit" else 3
            
            fig.add_trace(go.Scatter(
                x=center_data["date"],
                y=center_data["stock_qty"],
                mode='lines+markers',
                name=center,
                line=dict(dash=line_style, width=line_width),
                hovertemplate=f'<b>{center}</b><br>' +
                             '날짜: %{x}<br>' +
                             '재고: %{y:,}<br>' +
                             '<extra></extra>'
            ))
    
    # 레이아웃 설정
    fig.update_layout(
        title=f"SKU {sku} 재고 추이",
        xaxis_title="날짜",
        yaxis_title="재고 수량",
        hovermode='x unified',
        height=400
    )
    
    # Y축 포맷
    fig.update_yaxis(tickformat=",")
    
    # 차트 표시
    st.plotly_chart(fig, use_container_width=True)
