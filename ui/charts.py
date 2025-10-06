import plotly.graph_objects as go
from plotly.subplots import make_subplots

def create_price_chart(df, symbol, timeframe, sl=None, tp=None):
    """
    Crea un grafico del prezzo con candele, medie mobili, RSI e volumi.
    Aggiunge linee orizzontali per Stop Loss e Take Profit se forniti.
    """
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, row_heights=[0.7, 0.3])

    # Grafico a candele
    fig.add_trace(go.Candlestick(x=df['time'],
                                 open=df['open'],
                                 high=df['high'],
                                 low=df['low'],
                                 close=df['close'],
                                 name='Candele'), row=1, col=1)

    # Medie Mobili
    if 'EMA_21' in df.columns:
        fig.add_trace(go.Scatter(x=df['time'], y=df['EMA_21'], mode='lines', name='EMA 21', line=dict(color='orange', width=1)), row=1, col=1)
    if 'EMA_50' in df.columns:
        fig.add_trace(go.Scatter(x=df['time'], y=df['EMA_50'], mode='lines', name='EMA 50', line=dict(color='blue', width=1)), row=1, col=1)

    # Aggiunta linee SL e TP
    if sl and sl > 0:
        fig.add_hline(y=sl, line_dash="dash", line_color="red", annotation_text="Stop Loss", 
                      annotation_position="bottom right", row=1, col=1)
    if tp and tp > 0:
        fig.add_hline(y=tp, line_dash="dash", line_color="green", annotation_text="Take Profit", 
                      annotation_position="bottom right", row=1, col=1)

    # Grafico RSI
    if 'RSI_14' in df.columns:
        fig.add_trace(go.Scatter(x=df['time'], y=df['RSI_14'], mode='lines', name='RSI', line=dict(color='purple')), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="gray", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="gray", row=2, col=1)

    # Layout
    fig.update_layout(
        title=f'Grafico Prezzo {symbol} - Timeframe {timeframe}',
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template='plotly_dark'
    )
    fig.update_yaxes(title_text="Prezzo ($)", row=1, col=1)
    fig.update_yaxes(title_text="RSI", row=2, col=1)
    
    return fig
