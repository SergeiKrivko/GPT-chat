import os
import shutil
import sys

from src import config

SRC_PATH = f'dist/{config.APP_NAME}' if len(sys.argv) < 2 else sys.argv[1]
DST_APP_PATH = f'dist/debpkg/opt/{config.ORGANISATION_NAME}/{config.APP_NAME}'

shutil.copytree(SRC_PATH, DST_APP_PATH)

os.makedirs('dist/debpkg/usr/share/applications', exist_ok=True)
with open(f'dist/debpkg/usr/share/applications/{config.APP_NAME}.desktop', 'w', encoding='utf-8') as f:
    f.write(f"""[Desktop Entry]
Version={config.APP_VERSION}
Name={config.APP_NAME}
GenericName=Web Browser
GenericName[ar]=متصفح الشبكة
GenericName[bg]=Уеб браузър
GenericName[ca]=Navegador web
GenericName[cs]=WWW prohlížeč
GenericName[da]=Browser
GenericName[de]=Web-Browser
GenericName[el]=Περιηγητής ιστού
GenericName[en_GB]=Web Browser
GenericName[es]=Navegador web
GenericName[et]=Veebibrauser
GenericName[fi]=WWW-selain
GenericName[fr]=Navigateur Web
GenericName[gu]=વેબ બ્રાઉઝર
GenericName[he]=דפדפן אינטרנט
GenericName[hi]=वेब ब्राउज़र
GenericName[hu]=Webböngésző
GenericName[it]=Browser Web
GenericName[ja]=ウェブブラウザ
GenericName[kn]=ಜಾಲ ವೀಕ್ಷಕ
GenericName[ko]=웹 브라우저
GenericName[lt]=Žiniatinklio naršyklė
GenericName[lv]=Tīmekļa pārlūks
GenericName[ml]=വെബ് ബ്രൌസര്‍
GenericName[mr]=वेब ब्राऊजर
GenericName[nb]=Nettleser
GenericName[nl]=Webbrowser
GenericName[pl]=Przeglądarka WWW
GenericName[pt]=Navegador Web
GenericName[pt_BR]=Navegador da Internet
GenericName[ro]=Navigator de Internet
GenericName[ru]=Веб-браузер
GenericName[sl]=Spletni brskalnik
GenericName[sv]=Webbläsare
GenericName[ta]=இணைய உலாவி
GenericName[th]=เว็บเบราว์เซอร์
GenericName[tr]=Web Tarayıcı
GenericName[uk]=Навігатор Тенет
GenericName[zh_CN]=网页浏览器
GenericName[zh_HK]=網頁瀏覽器
GenericName[zh_TW]=網頁瀏覽器
# Not translated in KDE, from Epiphany 2.26.1-0ubuntu1.
GenericName[bn]=ওয়েব ব্রাউজার
GenericName[fil]=Web Browser
GenericName[hr]=Web preglednik
GenericName[id]=Browser Web
GenericName[or]=ଓ୍ବେବ ବ୍ରାଉଜର
GenericName[sk]=WWW prehliadač
GenericName[sr]=Интернет прегледник
GenericName[te]=మహాతల అన్వేషి
GenericName[vi]=Bộ duyệt Web
# Gnome and KDE 3 uses Comment.
Comment=Access the Internet
Comment[ar]=الدخول إلى الإنترنت
Comment[bg]=Достъп до интернет
Comment[bn]=ইন্টারনেটটি অ্যাক্সেস করুন
Comment[ca]=Accedeix a Internet
Comment[cs]=Přístup k internetu
Comment[da]=Få adgang til internettet
Comment[de]=Internetzugriff
Comment[el]=Πρόσβαση στο Διαδίκτυο
Comment[en_GB]=Access the Internet
Comment[es]=Accede a Internet.
Comment[et]=Pääs Internetti
Comment[fi]=Käytä internetiä
Comment[fil]=I-access ang Internet
Comment[fr]=Accéder à Internet
Comment[gu]=ઇંટરનેટ ઍક્સેસ કરો
Comment[he]=גישה אל האינטרנט
Comment[hi]=इंटरनेट तक पहुंच स्थापित करें
Comment[hr]=Pristup Internetu
Comment[hu]=Internetelérés
Comment[id]=Akses Internet
Comment[it]=Accesso a Internet
Comment[ja]=インターネットにアクセス
Comment[kn]=ಇಂಟರ್ನೆಟ್ ಅನ್ನು ಪ್ರವೇಶಿಸಿ
Comment[ko]=인터넷 연결
Comment[lt]=Interneto prieiga
Comment[lv]=Piekļūt internetam
Comment[ml]=ഇന്റര്‍‌നെറ്റ് ആക്‌സസ് ചെയ്യുക
Comment[mr]=इंटरनेटमध्ये प्रवेश करा
Comment[nb]=Gå til Internett
Comment[nl]=Verbinding maken met internet
Comment[or]=ଇଣ୍ଟର୍ନେଟ୍ ପ୍ରବେଶ କରନ୍ତୁ
Comment[pl]=Skorzystaj z internetu
Comment[pt]=Aceder à Internet
Comment[pt_BR]=Acessar a internet
Comment[ro]=Accesaţi Internetul
Comment[ru]=Доступ в Интернет
Comment[sk]=Prístup do siete Internet
Comment[sl]=Dostop do interneta
Comment[sr]=Приступите Интернету
Comment[sv]=Gå ut på Internet
Comment[ta]=இணையத்தை அணுகுதல்
Comment[te]=ఇంటర్నెట్‌ను ఆక్సెస్ చెయ్యండి
Comment[th]=เข้าถึงอินเทอร์เน็ต
Comment[tr]=İnternet'e erişin
Comment[uk]=Доступ до Інтернету
Comment[vi]=Truy cập Internet
Comment[zh_CN]=访问互联网
Comment[zh_HK]=連線到網際網路
Comment[zh_TW]=連線到網際網路
Exec=/opt/{config.ORGANISATION_NAME}/{config.APP_NAME}/{config.APP_NAME}
StartupNotify=true
Terminal=false
Icon=/opt/{config.ORGANISATION_NAME}/{config.APP_NAME}/_internal/icon.png
Type=Application
Categories=Network;WebBrowser;
""")
