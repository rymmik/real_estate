import requests
import json
import folium
import geopandas
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from geopy.distance import great_circle
import math
import statsmodels.formula.api as smf
from pylab import *
import seaborn as sns
import statsmodels.api as sm
import statsmodels.stats.api as sms
from statsmodels.compat import lzip
import matplotlib.pyplot as plt
from stargazer.stargazer import Stargazer
import matplotlib.ticker as ticker

pd.set_option('display.max_columns',30)
pd.set_option('display.width', 1000)

#######  Zebranie linków z ogłoszeniami - czas trwania ok. 10 min
def zbieranie_linkow():
    linki=[]
    ####Deklaracja liczby stron z ogłoszeniami
    strona1 = 'https://www.otodom.pl/pl/oferty/sprzedaz/mieszkanie/warszawa?distanceRadius=0&page=1&limit=72&market=ALL&locations=%5Bcities_6-26%5D&by=DEFAULT&direction=DESC&viewType=listing&lang=pl&searchingCriteria=sprzedaz&searchingCriteria=mieszkanie&searchingCriteria=cala-polska'
    page = requests.get(strona1)
    soup = BeautifulSoup(page.content, 'html.parser')
    skrypt = soup.find_all('script', id='__NEXT_DATA__')[0].text.strip()
    data = json.loads(skrypt)
    l_stron = data['props']['pageProps']['data']['searchAds']['pagination']['totalPages']
    #utworzenie listy wszystkich stron z ogłoszeniami
    pages=['https://www.otodom.pl/pl/oferty/sprzedaz/mieszkanie/warszawa?distanceRadius=0&page='+str(i)+'&limit=72&market=ALL&locations=%5Bcities_6-26%5D&by=DEFAULT&direction=DESC&viewType=listing&lang=pl&searchingCriteria=sprzedaz&searchingCriteria=mieszkanie&searchingCriteria=cala-polska' for i in range(1,l_stron,1)]

    #######zebranie linków
    for i in pages:
        page = requests.get(i)
        soup = BeautifulSoup(page.content, 'html.parser')
        skrypt=''
        ### W przypadku błędnego wczytania kodu źródłowego próbujemy jeszcze 3 razy
        try:
            skrypt = soup.find_all('script', id='__NEXT_DATA__')[0].text.strip()
        except IndexError:
            counter = 0
            while counter < 3:
                try:
                    skrypt = soup.find_all('script', id='__NEXT_DATA__')[0].text.strip()
                except IndexError:
                    counter+=1
                if skrypt!='':
                    break
            if skrypt=='':
                continue
        data=json.loads(skrypt)
        for j in range(len(data['props']['pageProps']['data']['searchAds']['items'])):
            linki.append('https://www.otodom.pl/pl/oferta/'+data['props']['pageProps']['data']['searchAds']['items'][j]['slug'])
    ######eksport do csv
    linki=list(set(linki)) #usuwanie duplikatów
    export1=pd.DataFrame(linki)
    export1.to_csv('linki.csv', index = False, header=False)

#######  Scrapowanie danych z zebranych linków - czas trwania ok. 3 godziny (wymagana podmiana ścieżki do importu i exportu) #do dodania wysokość budynku
def scraping():
    # wczytanie linków
    linki=pd.read_csv('linki.csv', header=None)
    linki=linki[0].values.tolist()
    # zmienne
    cena=[]
    cena_m2=[]
    dzielnica=[]
    wspolrzedne_szerokosc=[]
    wspolrzedne_wysokosc=[]
    powierzchnia=[]
    wlasnosc=[]
    pokoje=[]
    stan=[]
    pietro=[]
    pietro_max=[]
    czynsz=[]
    rok_budowy=[]
    zabudowa=[]
    material=[]
    winda=[]
    linki2=[]
    rynek=[]
    balkon=[]
    ogrod=[]
    taras=[]
    ogloszeniodawca=[]
    #####scrapping
    for i in linki:
        page = requests.get(i)
        soup = BeautifulSoup(page.content, 'html.parser')
        skrypt=''
        ### W przypadku błędnego wczytania kodu źródłowego próbujemy jeszcze 3 razy
        try:
            skrypt = soup.find_all('script', id='__NEXT_DATA__')[0].text.strip()
        except IndexError:
            counter = 0
            while counter < 3:
                try:
                    skrypt = soup.find_all('script', id='__NEXT_DATA__')[0].text.strip()
                except IndexError:
                    counter+=1
                if skrypt!='':
                    break
            if skrypt=='':
                continue
        data=json.loads(skrypt)
        #### pomijanie zakończonego ogłoszenia lub bez tabelki z informacjami dodatkowymi
        try:
            rok_budowy.append(int(data['props']['pageProps']['ad']['additionalInformation'][3]['values'][0]) if data['props']['pageProps']['ad']['additionalInformation'][3]['values'] != [] else 'NA')  # rok budowy
        except (KeyError, IndexError):
            continue
        powierzchnia.append(float(data['props']['pageProps']['ad']['topInformation'][0]['values'][0]))    #powierzchnia
        wlasnosc.append(data['props']['pageProps']['ad']['topInformation'][1]['values'][0] if data['props']['pageProps']['ad']['topInformation'][1]['values']!=[] else 'NA') #własność
        zabudowa.append(data['props']['pageProps']['ad']['additionalInformation'][4]['values'][0] if data['props']['pageProps']['ad']['additionalInformation'][4]['values']!=[] else 'NA') #zabudowa
        stan.append(data['props']['pageProps']['ad']['topInformation'][3]['values'][0] if data['props']['pageProps']['ad']['topInformation'][3]['values']!=[] else 'NA') #stan
        if data['props']['pageProps']['ad']['topInformation'][4]['values']==[] or data['props']['pageProps']['ad']['topInformation'][4]['values'][0]=='' or data['props']['pageProps']['ad']['topInformation'][4]['values'][0][-5:]=='er_10' or data['props']['pageProps']['ad']['topInformation'][4]['values'][0][-2:]=='et' or data['props']['pageProps']['ad']['topInformation'][4]['values'][0][-2:]=='ar':
            pietro.append('NA')
            pietro_max.append('NA')
        elif data['props']['pageProps']['ad']['topInformation'][4]['values'][0][-2:]=='or': #parter
            pietro.append(0)
            pietro_max.append(data['props']['pageProps']['ad']['topInformation'][4]['values'][1][1:])
        elif data['props']['pageProps']['ad']['topInformation'][4]['values'][0][-5:]=='or_10': #10 piętro
            pietro.append(10)
            pietro_max.append(data['props']['pageProps']['ad']['topInformation'][4]['values'][1][1:])
        else:
            pietro.append(int(data['props']['pageProps']['ad']['topInformation'][4]['values'][0][-1:]))
            pietro_max.append(data['props']['pageProps']['ad']['topInformation'][4]['values'][1][1:])
        cena.append(int(float(data['props']['pageProps']['ad']['characteristics'][0]['localizedValue'][:-3].replace(" ", "").replace(",", "."))) if data['props']['pageProps']['ad']['characteristics'][0]['localizedValue']!='Zapytaj o cenę' else 'NA') #cena
        cena_m2.append(int(float(data['props']['pageProps']['ad']['characteristics'][2]['localizedValue'][:-5].replace(" ", "").replace(",", "."))) if data['props']['pageProps']['ad']['characteristics'][2]['localizedValue']!='' else 'NA') #cena_m2
        czynsz.append(data['props']['pageProps']['ad']['topInformation'][6]['values'][0][:-3] if data['props']['pageProps']['ad']['topInformation'][6]['values']!=[] else 'NA') #czynsz
        if data['props']['pageProps']['ad']['topInformation'][2]['values']==[]:
            pokoje.append('NA')
        elif data['props']['pageProps']['ad']['topInformation'][2]['values'][0]=='rooms_num::more':
            pokoje.append('NA')
        else:
            pokoje.append(int(data['props']['pageProps']['ad']['topInformation'][2]['values'][0])) #pokoje
        material.append(data['props']['pageProps']['ad']['additionalInformation'][11]['values'][0] if data['props']['pageProps']['ad']['additionalInformation'][11]['values']!=[] else 'NA') #materiał
        winda.append(1 if data['props']['pageProps']['ad']['additionalInformation'][6]['values'][0][-1:]=='y' else 0) #winda
        dzielnica.append(data['props']['pageProps']['ad']['breadcrumbs'][3]['locative']) #dzielnica
        wspolrzedne_szerokosc.append(data['props']['pageProps']['ad']['location']['coordinates']['latitude']) #wsp_szer
        wspolrzedne_wysokosc.append(data['props']['pageProps']['ad']['location']['coordinates']['longitude']) #wsp_wys
        rynek.append(data['props']['pageProps']['ad']['additionalInformation'][0]['values'][0] if data['props']['pageProps']['ad']['additionalInformation'][1]['values']!=[] else 'NA')
        if 'extras_types::balcony' in data['props']['pageProps']['ad']['topInformation'][5]['values']:
            balkon.append(1)
        else:
            balkon.append(0)
        if 'extras_types::garden' in data['props']['pageProps']['ad']['topInformation'][5]['values']:
            ogrod.append(1)
        else:
            ogrod.append(0)
        if 'extras_types::terrace' in data['props']['pageProps']['ad']['topInformation'][5]['values']:
            taras.append(1)
        else:
            taras.append(0)
        ogloszeniodawca.append(data['props']['pageProps']['ad']['additionalInformation'][1]['values'][0] if data['props']['pageProps']['ad']['additionalInformation'][1]['values']!=[] else 'NA')
        linki2.append(i)

    #####eksport do csv
    export2=pd.DataFrame({'dzielnica':dzielnica, 'cena':cena, 'cena_m2':cena_m2, 'powierzchnia':powierzchnia, 'rok_budowy':rok_budowy, 'wlasnosc':wlasnosc, 'zabudowa':zabudowa, 'stan':stan, 'pietro':pietro, 'pietro_max':pietro_max, 'czynsz':czynsz, 'pokoje':pokoje, 'material':material, 'winda':winda, 'rynek':rynek, 'ogloszeniodawca':ogloszeniodawca, 'balkon':balkon, 'ogrod':ogrod, 'taras':taras, 'wspolrzedne_szerokosc':wspolrzedne_szerokosc, 'wspolrzedne_wysokosc':wspolrzedne_wysokosc, 'link':linki2})
    export2.to_csv('C:/Users/mikol/Documents/python-projects/dane.csv', index = False, header=True)

######   Policzenie odległości między najbliższą stacją metra oraz pałacem kultury - czas trwania ok. 5 min
def odleglosci():
    data=pd.read_csv('C:/Users/mikol/Documents/python-projects/dane.csv', delimiter=',')
    print(data)
    metro=pd.read_csv('stacje_metra.csv', delimiter=';')
    odleglosci_metro=[]
    odleglosc_metro=[]
    odleglosc_centrum=[]
    PK=(52.23172, 21.00605)
    for j in range(len(data)):
        for i in range(len(metro)):
            odleglosci_metro.append(great_circle((metro.wspolrzedne_szerokosc[i], metro.wspolrzedne_wysokosc[i]),(data.wspolrzedne_szerokosc[j],data.wspolrzedne_wysokosc[j])).km)
        odleglosc_metro.append(min(odleglosci_metro))
        odleglosc_centrum.append(great_circle(PK,(data.wspolrzedne_szerokosc[j],data.wspolrzedne_wysokosc[j])).km)
        odleglosci_metro.clear()
    data['odleglosc_metro']=odleglosc_metro
    data['odleglosc_centrum']=odleglosc_centrum
    data.to_csv('C:/Users/mikol/Documents/python-projects/dane.csv', index=False, header=True)

#zbieranie_linkow()
#scraping()
#odleglosci()

#####wczytanie danych
data=pd.read_csv('dane_nowe.csv')

#statystyki opisowe zmiennych
render=data.describe().T
print(render)

#####filtrowanie danych
#####Od 2007 roku zabronione jest stosowane spółdzielczej formy własności, a więc wszystkie brakujące dane o własności od 2008 roku uzupełniam jako 'pełna własność'
data.loc[data['rok_budowy'] >= 2008, 'wlasnosc'] = 'building_ownership::full_ownership'
#ograniczenie danych na potrzebę modelu
data=data[((data.wlasnosc=='building_ownership::limited_ownership') | (data.wlasnosc=='building_ownership::full_ownership'))&(data.rynek=='market::secondary')&(data.rok_budowy<2024)&(data.rok_budowy>1943)&(data.cena_m2>=2000)&(data.odleglosc_centrum<=20)]
#####usuniecie zbednych kolumn
del data['cena'] #to cena za m2 jest wyjaśniana
del data['dzielnica'] #wykorzystuje dokładniejsze zmienne lokalizacyjne
del data['zabudowa'] #duże zróżnicowanie i dużo brakujących danych
del data['pokoje'] #zmienna powierzchnia jest dokładniejsza, wystąpiłaby autokorelacja
del data['czynsz'] #bardzo dużo brakujących danych
del data['material'] #duże zróżnicowanie, mało istotne
del data['rynek'] #badanie różnych rynków nie ma sensu
del data['ogrod'] #malo obserwacji
data=data.dropna().reset_index(drop=True)

#####zamiana zmiennych jakościowych na binarne
data['agencja']=[1 if i=='advertiser_type::agency' else 0 for i in data.ogloszeniodawca]
data['spoldzielcze']=[1 if i=='building_ownership::limited_ownership' else 0 for i in data.wlasnosc]
data['remont']=[1 if i=='construction_status::to_renovation' else 0 for i in data.stan]
data['wykonczenie']=[1 if i=='construction_status::to_completion' else 0 for i in data.stan]
del data['stan'] #uwzględnione w zmiennej 'remont' i 'wykonczenie'
del data['wlasnosc'] #uwzględnione w zmiennej 'spoldzielcze'
del data['ogloszeniodawca'] #uwzględnione w zmiennej 'agencja'
del data['link']

#Przedstawienie obserwacji na mapie Warszawy
def mapa():
    ###Utworzenie mapy
    m = folium.Map(location=[52.24004471408262, 21.01715492888584], zoom_start=12, tiles="OpenStreetMap")
    #Granice Warszawy
    jed = geopandas.read_file('C:/Users/mikol/Documents/python-projects/A02_Granice_powiatow.shp')
    jed=jed[jed.JPT_KOD_JE=='1465']
    folium.GeoJson(jed).add_to(m)
    #, style_function=lambda x: {"fillColor": 'transparent'}, #można usunąć poświatę pola Warszawy
    #Punkty na mapie z gradacją kolorów
    q1=data.cena_m2.quantile(0.25)
    q2=data.cena_m2.quantile(0.5)
    q3=data.cena_m2.quantile(0.75)
    for index, row in data.iterrows():
        value=row['cena_m2']
        if value > q3:
            color = 'red'
        elif value >= q2:
            color = 'orange'
        elif value >= q1:
            color = 'yellow'
        else:
            color = 'green'
        folium.CircleMarker([row['wspolrzedne_szerokosc'], row['wspolrzedne_wysokosc']], radius=2,  color=color, fill=True, fill_color=color).add_to(m)
    # Legenda kolorów na mapie
    legend_html = '''
         <div style="position: fixed; 
                     bottom: 50px; left: 50px; width: 280px; height: 260px; 
                     border: 2px solid grey; z-index: 9999; font-size: 35px;
                     background-color: white; padding: 5px;">
          <strong>Legenda</strong><br>
          <span style='color:red'>&#9679;</span> > 16385 <br>
          <span style='color:orange'>&#9679;</span> 13698 - 16385 <br>
          <span style='color:yellow'>&#9679;</span> 11589 - 13698 <br>
          <span style='color:green'>&#9679;</span> < 11589 <br>
         </div>
         '''
    m.get_root().html.add_child(folium.Element(legend_html))
    folium.LayerControl().add_to(m)
    #Zapis mapy
    m.save("mapa.html")
#mapa()
del data['wspolrzedne_szerokosc']
del data['wspolrzedne_wysokosc']



##### Testy do walidacji modeli ekonometrycznych

nam2 = ['JB statistic', 'p-value', 'skewness', 'kurtosis']
def testy(model):
    nam = ['Statistic', 'p-value', 'f-value', 'f p-value']
    for name, value in globals().items():
        if value is model:
            print('MODEL '+ name[-1:])
    print("test RESET:", sms.linear_reset(model, power=3, test_type='fitted'))
    print("test Breuscha-Pagana:", lzip(nam, sms.het_breuschpagan(model.resid, model.model.exog)))
    print("test White'a:", lzip(nam, sms.het_white(model.resid, model.model.exog)))
    print("test Breuscha-Godfreya:", lzip(nam, sms.acorr_breusch_godfrey(model)))
    print(model.summary())

###Test VIF
def get_vif(exogs, data):
    vif_dict, tolerance_dict = {}, {}
    for exog in exogs:
        not_exog = [i for i in exogs if i != exog]
        formula = f"{exog} ~ {' + '.join(not_exog)}"
        r_squared = smf.ols(formula, data=data).fit().rsquared
        vif = 1/(1 - r_squared)
        vif_dict[exog] = vif
        tolerance = 1 - r_squared
        tolerance_dict[exog] = tolerance
    df_vif = pd.DataFrame({'VIF': vif_dict, 'Tolerance': tolerance_dict})
    return df_vif


## Wykres korelacji zmiennych
corr=data.corr(method='pearson')
sns.heatmap(corr, cmap="Reds",annot=True)
tight_layout()
plt.show()

#Wykresy opisowe zmiennych
zmienne=['rok_budowy', 'powierzchnia', 'pietro','pietro_max','odleglosc_metro', 'odleglosc_centrum']
for zmienna in zmienne:
    fig, axes = plt.subplots(1, 3, figsize=(15,5))
    sns.regplot(data=data, x=zmienna, y="cena_m2", ci=None, line_kws = {"color": "red"}, scatter_kws = {"color": "blue", "alpha": 0.4}, ax=axes[0])
    sns.boxplot(data=data, y=zmienna, ax=axes[1])
    sns.histplot(data=data, x=zmienna, color='#A49C41', edgecolor="black", bins=30, kde=True, stat="density", ax=axes[2]).lines[0].set_color('darkblue')
    plt.show()

#Logarytmowanie ceny i porównanie histogramów
data['ln_cena_m2']=[math.log(i) for i in data.cena_m2]
fig, axes = plt.subplots(1, 2, figsize=(8,4))
sns.histplot(data['cena_m2'], color='#A49C41', edgecolor="black", bins=30, kde=True, stat="density", ax=axes[0]).lines[0].set_color('darkblue')
sns.histplot(data['ln_cena_m2'], color='#A49C41', edgecolor="black", bins=30, kde=True, stat="density", ax=axes[1]).lines[0].set_color('darkblue')
tight_layout()
plt.show()
print("TEST JB, cena_m2:", lzip(nam2, sms.jarque_bera(data.cena_m2)))
print("TEST JB, ln_cena_m2:", lzip(nam2, sms.jarque_bera(data.ln_cena_m2)))

# #Logarytmowanie odleglosci od centrum i porównanie wykresów
data['ln_odleglosc_centrum']=[math.log(i+1) for i in data.odleglosc_centrum]
fig, axes = plt.subplots(2, 2, figsize=(8,8))
sns.histplot(data['odleglosc_centrum'], color='#A49C41', edgecolor="black", bins=30, kde=True, stat="density", ax=axes[0,0]).lines[0].set_color('darkblue')
sns.histplot(data['ln_odleglosc_centrum'], color='#A49C41', edgecolor="black", bins=30, kde=True, stat="density", ax=axes[0,1]).lines[0].set_color('darkblue')
sns.regplot(x="odleglosc_centrum", y="ln_cena_m2", data=data, ci=None, line_kws = {"color": "red"}, scatter_kws = {"color": "blue", "alpha": 0.4}, ax=axes[1,0])
sns.regplot(x="ln_odleglosc_centrum", y="ln_cena_m2", data=data, ci=None, line_kws = {"color": "red"}, scatter_kws = {"color": "blue", "alpha": 0.4}, ax=axes[1,1])
tight_layout()
plt.show()

# #Logarytmowanie odleglosci od metra i porównanie wykresów
data['ln_odleglosc_metro']=[math.log(i+1) for i in data.odleglosc_metro]
fig, axes = plt.subplots(2, 2, figsize=(8,8))
sns.histplot(data['odleglosc_metro'], color='#A49C41', edgecolor="black", bins=30, kde=True, stat="density", ax=axes[0,0]).lines[0].set_color('darkblue')
sns.histplot(data['ln_odleglosc_metro'], color='#A49C41', edgecolor="black", bins=30, kde=True, stat="density", ax=axes[0,1]).lines[0].set_color('darkblue')
sns.regplot(x="odleglosc_metro", y="ln_cena_m2", data=data, ci=None, line_kws = {"color": "red"}, scatter_kws = {"color": "blue", "alpha": 0.4}, ax=axes[1,0])
sns.regplot(x="ln_odleglosc_metro", y="ln_cena_m2", data=data, ci=None, line_kws = {"color": "red"}, scatter_kws = {"color": "blue", "alpha": 0.4}, ax=axes[1,1])
tight_layout()
plt.show()

#Logarytmowanie powierzchni
data['ln_powierzchnia']=[math.log(i) for i in data.powierzchnia]
fig, axes = plt.subplots(2, 2, figsize=(8,8))
sns.histplot(data['powierzchnia'], color='#A49C41', edgecolor="black", bins=30, kde=True, stat="density", ax=axes[0,0]).lines[0].set_color('darkblue')
sns.histplot(data['ln_powierzchnia'], color='#A49C41', edgecolor="black", bins=30, kde=True, stat="density", ax=axes[0,1]).lines[0].set_color('darkblue')
sns.regplot(x="powierzchnia", y="ln_cena_m2", data=data, ci=None, line_kws = {"color": "red"}, scatter_kws = {"color": "blue", "alpha": 0.4}, ax=axes[1,0])
sns.regplot(x="ln_powierzchnia", y="ln_cena_m2", data=data, ci=None, line_kws = {"color": "red"}, scatter_kws = {"color": "blue", "alpha": 0.4}, ax=axes[1,1])
tight_layout()
plt.show()
print("TEST JB, powierzchnia:", lzip(nam2, sms.jarque_bera(data.powierzchnia)))
print("TEST JB, ln_powierzchnia:", lzip(nam2, sms.jarque_bera(data.ln_powierzchnia)))


#Podział roku budowy na 2 przedziały: stare i nowe budownictwo. Przedstawienie wykresów.
data['nowe_bud']=[1 if i>1989 else 0 for i in data.rok_budowy]
data['rok_budowy_1989']=data.rok_budowy-1989
data['rok_budowy2']=data.nowe_bud*data.rok_budowy_1989
fig, axes = plt.subplots(1, 2, figsize=(8,4))
sns.histplot(data['rok_budowy'], color='#A49C41', edgecolor="black", bins=30, kde=True, stat="density", ax=axes[0]).lines[0].set_color('darkblue')
sns.regplot(x="rok_budowy", y="ln_cena_m2", data=data, ci=None, line_kws = {"color": "red"}, scatter_kws = {"color": "blue", "alpha": 0.4}, ax=axes[1])
tight_layout()
plt.show()

#Przekształcenie zmiennej piętro
data['pietro_skala']=data.pietro/data.pietro_max
data['pietro_24']=data.pietro_skala-0.24
data['pietro_skala_24']=[1 if i>0.24 else 0 for i in data.pietro_skala]
data['pietro_skala2']=data.pietro_24*data.pietro_skala_24

#Wykres korelacji pietro_skala
corr = []
for i in np.arange(0.01, 1, 0.01):
    df=data[data['pietro_skala']<=i]
    if math.isnan(df['pietro_skala'].corr(df['ln_cena_m2'])) == False:
        corr.append(float(df['pietro_skala'].corr(df['ln_cena_m2'])))
label=[]
for i in range(1 * (100 - len(corr)), 95, 1):
    label.append('0,'+str(i))
sns.barplot(x=label, y=corr[:-5], color='purple')
plt.xlabel("pietro/pietro_max")
plt.ylabel("korelacja ze zmienną ln_cena_m2")
plt.gca().xaxis.set_major_locator(ticker.MultipleLocator(6))
tight_layout()
plt.show()


#statystyki opisowe zmiennych
render=data.describe().T
print(render)

#####Testowanie modeli
#model bazowy
m1=smf.ols(formula='cena_m2 ~ rok_budowy + spoldzielcze + remont + wykonczenie + winda + powierzchnia  + pietro + pietro_max + balkon + taras + odleglosc_metro + odleglosc_centrum + agencja', data=data).fit()
testy(m1)

#model ze zlogarytmowaną ceną_m2
m2=smf.ols(formula='ln_cena_m2 ~ rok_budowy + spoldzielcze + remont + wykonczenie + winda + powierzchnia + pietro + pietro_max + balkon + taras + odleglosc_metro + odleglosc_centrum + agencja', data=data).fit()
testy(m2)

#wyrzucenie nieistotnej zmiennej pietro
m3=smf.ols(formula='ln_cena_m2 ~ rok_budowy + spoldzielcze + remont + wykonczenie + rok_budowy2 + winda + powierzchnia + pietro + pietro_max + balkon + taras + odleglosc_metro + odleglosc_centrum + agencja', data=data).fit()
testy(m3)

#wprowadzenie przedziału dla zmiennej rok_budowy
m4=smf.ols(formula='ln_cena_m2 ~ rok_budowy + spoldzielcze + remont + wykonczenie + rok_budowy2 + winda + powierzchnia + pietro_skala2 + pietro_skala + balkon + taras + odleglosc_metro + odleglosc_centrum + agencja', data=data).fit()
testy(m4)

#zastosowanie macierzy odpornej white'a
m5=smf.ols(formula='ln_cena_m2 ~ rok_budowy + spoldzielcze + remont + wykonczenie + rok_budowy2 + winda + ln_powierzchnia + pietro_skala2 + pietro_skala + balkon + taras + odleglosc_metro + odleglosc_centrum + agencja', data=data).fit()
testy(m5)

#zastosowanie macierzy odpornej white'a
m6=smf.ols(formula='ln_cena_m2 ~ rok_budowy + spoldzielcze + remont + wykonczenie + rok_budowy2 + winda + ln_powierzchnia + pietro_skala2 + pietro_skala + balkon + taras + odleglosc_metro + odleglosc_centrum + agencja', data=data).fit(cov_type = 'HC0')
testy(m6)


#Porównanie modeli
print(Stargazer([m1, m2, m3, m4, m5, m6]).render_html())

#Obliczenie VIF
zmienne = ['rok_budowy', 'winda', 'ln_powierzchnia', 'pietro_skala', 'balkon', 'taras', 'odleglosc_metro', 'odleglosc_centrum', 'agencja', 'spoldzielcze', 'remont', 'wykonczenie']
print(get_vif(exogs = zmienne, data = data))

#Wykres reszt
data['residuals'] = m6.resid
data['fitted values'] = m6.predict()
sns.residplot(data = data, x = 'fitted values' , y = 'residuals', lowess = True, line_kws = dict(color = 'g'))
tight_layout()
plt.show()

#wykres dziwigni
h_lev = (2*len(m6.params))/m6.nobs
sm.graphics.influence_plot(m6, criterion = 'Cooks', title=None)
axvline(x = round(h_lev, 2), color = 'g')
axhline(y=2, color = 'r')
axhline(y=-2, color = 'r')
plt.title("")
tight_layout()
plt.show()

#histogram składnika losowego
sns.histplot(m6.resid, color='#A49C41', edgecolor="black", bins=30, kde=True, stat="density").lines[0].set_color('darkblue')
plt.xlabel("Standardized residuals")
tight_layout()
plt.show()
print("TEST JB, reszty:", lzip(nam2, sms.jarque_bera(m6.resid)))

#obserwacje nietypowe
print(data.iloc[3101,:])
print(data.iloc[225,:])
print(data.iloc[3082,:])
print(data.iloc[2853,:])

#obserwacje nietypowe nie są usuwane ze względu na brak możliwości weryfikacji








