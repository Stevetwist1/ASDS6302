import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import requests 
import io



# Data Load
DF_PATH = 'C:/Users/Steve/OneDrive/Desktop/Python/ASDS6302/2015_Street_Tree_Census_-_Tree_Data_20250409.csv'
df = pd.read_csv(DF_PATH).dropna(subset=['latitude', 'longitude'])



# Drop any rows missing the coords
df = df.dropna(subset=["latitude","longitude"])


status_values = sorted(df['status'].dropna().unique())

# Precompute Static Analytics Figures
health_counts = df['health'].value_counts().reset_index()
health_counts.columns = ['health', 'count']
fig_bar = px.bar(
    health_counts,
    x='health',
    y='count',
    labels={'health':'Health','count':'Count'},
    color='health',
    color_discrete_map={'Good':'green','Fair':'yellow','Poor':'red'}
)
fig_hist = px.histogram(
    df[df['tree_dbh'] < 100],
    x='tree_dbh',
    nbins=20,
    labels={'tree_dbh':'DBH (cm)'},
    title='DBH Distribution (<100 cm)'
)

fig_pie_health = px.pie(
    health_counts,
    names='health',
    values='count',
    title='Health Distribution',
    color_discrete_map={'Good':'green','Fair':'yellow','Poor':'red'}
)
status_counts = df['status'].value_counts().reset_index()
status_counts.columns = ['status', 'count']
fig_pie_status = px.pie(
    status_counts,
    names='status',
    values='count',
    title='Status Distribution'
)

# Dash App Initialization
external_stylesheets = [dbc.themes.DARKLY]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.config.suppress_callback_exceptions = True
server = app.server
app.title = 'NYC Street Tree Census'

# Navbar
navbar = dbc.Navbar(
    dbc.Container([
        html.A(
            html.Img(src="/assets/d_spart1.png",
                height="100px",                      # adjust to fit
                style={"margin-right": "10px"},), className='navbar-brand fw-bold fs-3 text-white', href='/'),
        dbc.NavbarToggler(id='navbar-toggler'),
        dbc.Collapse(
            dbc.Nav(
                dbc.DropdownMenu(
                    label='Menu', nav=True, in_navbar=True,
                    children=[
                        dbc.DropdownMenuItem('Map View', href='/'),
                        dbc.DropdownMenuItem('Analytics', href='/analytics')
                    ]
                ), className='ms-auto', navbar=True
            ), id='navbar-collapse', navbar=True
        )
    ]), color='dark', dark=True
)

# Map Layout
map_layout = dbc.Container(fluid=True, children=[
    html.H1('NYC Street Tree Census', className='text-center text-white my-4'),
    dbc.Row([
        dbc.Col([html.Label('Health', className='text-white me-2'), dcc.Checklist(
            id='health-check',
            options=[{'label':h,'value':h} for h in health_counts['health']],
            value=list(health_counts['health']),
            inline=True
        )], width='auto')
    ], className='mb-4'),
    dcc.Graph(
        id='main-map',
        style={'width': '100%', 'height': '75vh', 'margin': '0', 'padding': '0'}
    ),
    html.H3('Map Data Table', className='text-white mt-4'),
    dash_table.DataTable(
        id='map-table',
        columns=[{'name':col.replace('_',' ').title(),'id':col} for col in ['tree_id','address','spc_common','health','status','council district']],
        page_size=10,
        filter_action='native',
        sort_action='native',
        style_header={'backgroundColor':'#212529','color':'white','fontWeight':'bold'},
        style_cell={'backgroundColor':'#343a40','color':'white'}
    ),
    html.Div('Developed by Steve Adjorlolo (2025)', className='text-center text-white my-4')
])

# Analytics Layout
analytics_layout = dbc.Container(fluid=True, children=[
    html.H1('NYC Street Tree Census', className='text-center text-white my-4'),
    html.H2('Analytics', className='text-white mb-4'),
    dbc.Row([
        dbc.Col(dcc.Graph(id='bar-health', figure=fig_bar), width=6),
        dbc.Col(dcc.Graph(id='histogram-dbh', figure=fig_hist), width=6)
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(id='pie-health', figure=fig_pie_health), width=6),
        dbc.Col(dcc.Graph(id='pie-status', figure=fig_pie_status), width=6)
    ]),
    html.H5('Status Map Gradient', className='text-white mt-4'),
    dcc.Tabs(
        id='status-tabs',
        value=status_values[0],
        children=[dcc.Tab(label=s, value=s) for s in status_values],
        colors={"border": "white", "primary": "white", "background": "#343a40"}
    ),
    dcc.Graph(id='analytics-map', style={'height': '50vh'}),
    html.Div('Developed by Steve Adjorlolo', className='text-center text-white my-4')
])

# App Layout
app.layout = html.Div([navbar, dcc.Location(id='url'), html.Div(id='page-content')])

# Routing Callback
@app.callback(Output('page-content','children'), Input('url','pathname'))
def render_page(pathname):
    return analytics_layout if pathname=='/analytics' else map_layout

# Map Callbacks
@app.callback(
    Output('main-map','figure'),
    Input('health-check','value')
)
def update_map(sel_h):
    d = df[df['health'].isin(sel_h)]
    agg = d.groupby('council district').agg(count=('tree_id','count'), latitude=('latitude','mean'), longitude=('longitude','mean')).reset_index()
    center={'lat':agg['latitude'].mean(),'lon':agg['longitude'].mean()}
    fig=px.scatter_mapbox(agg,lat='latitude',lon='longitude',size='count',color='count',zoom=10, hover_data={'count':True, 'council district':True},center=center)
    fig.update_layout(mapbox_style='open-street-map',paper_bgcolor='#343a40',plot_bgcolor='#343a40',coloraxis_colorbar=dict(tickfont=dict(color='white')))
    return fig

@app.callback(
    Output('map-table','data'),
    Input('health-check','value')
)
def update_table(sel_h):
    d=df[df['health'].isin(sel_h)]
    return d[['tree_id','address','spc_common','health','status','council district']].to_dict('records')

# Analytics Map Callback
@app.callback(
    Output('analytics-map','figure'),
    Input('status-tabs','value')
)
def update_analytics_map(sel_status):
    d = df[df['status']==sel_status]
    agg = d.groupby('council district').agg(count=('tree_id','count'), latitude=('latitude','mean'), longitude=('longitude','mean')).reset_index()
    center={'lat':agg['latitude'].mean(),'lon':agg['longitude'].mean()}
    color_scale={'Alive':['lightgreen','green'],'Fair':['lightblue','blue'],'Dead':['lightcoral','red']}.get(sel_status,['lightblue','darkblue'])
    fig=px.scatter_mapbox(agg,lat='latitude',lon='longitude',size='count',color='count',color_continuous_scale=color_scale,zoom=10,center=center)
    fig.update_layout(mapbox_style='open-street-map',paper_bgcolor='#343a40',plot_bgcolor='#343a40',coloraxis_colorbar=dict(title='Count',showticklabels=True,tickfont=dict(color='white')))
    return fig


if __name__ == '__main__':
    app.run(debug=True, port=8055)



