#!/usr/bin/env python3
"""Create supporting documents without modifying the approved manuscript."""
from pathlib import Path
import json
import sys
from docx.shared import Pt
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from cold_chain.documents import setup,paragraph,table,code,newpage,markdown_document,build_supplement,TITLE

def cover():
    d=setup();d.styles['Normal'].paragraph_format.line_spacing=1.05
    d.styles['Normal'].paragraph_format.space_after=Pt(7)
    d.sections[0].footer.paragraphs[0].clear()
    d.add_heading('Cover Letter',0)
    paragraph(d,'31 October 2026')
    paragraph(d,'Editor-in-Chief\nInternational Journal of Production Research')
    paragraph(d,'Dear Editor-in-Chief,')
    paragraph(d,f'Please consider my manuscript, “{TITLE}”, for publication as an original research article in the International Journal of Production Research.')
    paragraph(d,'The study addresses regional cold-chain warehouse location as a strategic production–distribution decision. Five active domain practitioners provide equally weighted pairwise judgments. Spherical fuzzy analytic hierarchy process weights are combined with EDAS, WASPAS, CoCoSo, TOPSIS and VIKOR to assess 15 Ankara districts against 13 criteria.')
    paragraph(d,'The contribution is an explicit distinction between stability under weight uncertainty and robustness to criterion design. Cross-method agreement, Borda consensus, 104 local weight perturbations, parameter sweeps, criterion deletions, strategic scenarios and 5,000 Dirichlet replications support a common-data comparison. Etimesgut leads the baseline consensus, followed by Yenimahalle and Mamak. The first-rank probabilities of the leading pair are 62.34% and 37.62%. Removing the cold-chain-risk criterion or jointly removing the related derived indicators selects Yenimahalle, showing why local weight stability alone is insufficient.')
    paragraph(d,'The work is relevant to the journal through facility location, production–distribution coordination, sustainable logistics and decision support under uncertainty. The findings guide district-level feasibility assessment and make the dependence of the recommendation on criterion design transparent.')
    paragraph(d,'The supplementary archive includes the practitioner matrices, decision inputs, executable Python code, all tabular and graphical outputs, complete simulation records and numerical verification scripts. The research received no external funding, and I declare no competing interests.')
    paragraph(d,'Thank you for considering this manuscript.')
    paragraph(d,'Yours sincerely,\nHüseyin Ali Sarıkaya\nDepartment of Industrial Engineering, Mudanya University, Bursa, Türkiye\nhuseyin.sarikaya@mudanya.edu.tr\nORCID: 0000-0001-5072-5067')
    path=ROOT/'docs/IJPR_Cover_Letter_Draft.docx';d.save(path);return path

def audit():
    check=json.loads((ROOT/'results/reproduction_check.json').read_text())
    d=setup();d.add_heading('Makale ve kod doğrulama raporu',0)
    paragraph(d,'31 Ekim 2026\nCold Chain Warehouse Location sürüm 2.0.0\nHüseyin Ali Sarıkaya')
    paragraph(d,'Supplementary Material paketi, onaylanan IJPR makalesinin sayısal yöntemlerini ve bulgularını yeniden üretmektedir. Ana makalenin dosyası, başlığı, bölüm yapısı, gerçek practitioners bilgisi ve özgün mimari şekli korunmuştur. Bu aşamada makale yeniden yazılmamıştır.')
    table(d,['Doğrulama','Sonuç'],[
        ['Tam hassasiyetli CSV karşılaştırması',f"{check['csv_files_compared']} dosya eşleşti"],
        ['Makale tabloları',f"{check['publication_tables_compared']} tablo, {check['table_cells_compared']:,} hücre birebir eşleşti".replace(',','.')],
        ['Özgün mimari şekil','Dosya baytları birebir aynı'],
        ['Ana makalenin diğer iki şekli','Yerel üretimde pikseller birebir aynı'],
        ['Sayısal birim testleri','8 test başarılı'],
        ['Genel yeniden üretim durumu',check['status']]],[3.9,2.8])
    d.add_heading('Doğrulanan temel bulgular',1)
    table(d,['Gösterge','Değer'],[
        ['Borda toplamları','Etimesgut 8; Yenimahalle 12; Mamak 16'],
        ['Kendall W','0,9071428571'],
        ['104 yerel ağırlık durumu','Etimesgut 98; Yenimahalle 6'],
        ['İlk sıra olasılığı','Etimesgut %62,34; Yenimahalle %37,62; Mamak %0,04'],
        ['İlk üçte yer alma','Etimesgut %99,98; Yenimahalle %99,86; Mamak %84,06'],
        ['Yapısal silme deneyi','C13 veya C11–C13 silindiğinde lider Yenimahalle']],[2.8,3.9])

    newpage(d,'Veri ve hesaplama kontrolleri')
    paragraph(d,'Kaynak çalışma kitabındaki C1–C9 için 135 gözlem, hesaplamada kullanılan CSV girdileriyle karşılaştırılmıştır. C10–C13 için 60 türetilmiş değer yeniden hesaplanmıştır. Beş practitionera ait toplam 845 dilsel matris girdisi Appendix B ile eşleşmektedir. P2 matrisindeki dört alt üçgen karşılıklılık kodlaması provenance/pairwise_encoding_log.csv dosyasında belgelenmiştir.')
    table(d,['Test','Kontrol edilen özellik'],[
        ['Bağımsız skaler hesap','Beş yöntemin vektörleştirilmiş skorları ayrı formül koduyla karşılaştırıldı'],
        ['Türetilmiş göstergeler','İşgücü, bağlantı, emisyon ve termal maruziyet hesapları'],
        ['SF ağırlıklar ve tutarlılık','Küresel uygulanabilirlik, karşılıklılık ve CR < 0,10'],
        ['Kriter silme','Sıfır ağırlık gerçek sütun silmeyle aynı sonucu veriyor'],
        ['Birim ve kimlik','Ölçü birimi ve satır sırası değişimi kontrolleri'],
        ['Eşit skorlar','Yöntemlerde ortalama sıra ve belirlenmiş konsensüs eşitlik kuralı'],
        ['Rastgele üretim','PCG64 ve seed 42 ile aynı ağırlık örnekleri'],
        ['Kaynak sonuç deneyi','Kaynak çalışma kitabının kayıtlı ağırlıklarıyla yöntem skorları']],[2.05,4.65],size=10)
    paragraph(d,'Monte Carlo standart sapması örneklem tanımıyla, yöntemler arası sıra standart sapması anakütle tanımıyla hesaplanır. Yüzdelik sıra aralıkları ampirik dağılımdan alınır. Tam hassasiyetli çıktı karşılaştırmasında bağıl tolerans 1e-11, mutlak tolerans 1e-12 kullanılır; makalede gösterilen tablo hücreleri metin ve değer olarak birebir karşılaştırılır.')
    paragraph(d,'Onaylı makaledeki 42 kaynakça girdisi ve kaynakça düzeni korunmuştur. Bu paket oluşturma aşamasında literatür yeniden değiştirilmemiştir. Hesaplama doğrulaması, girdi fiyatlarının veya saha ölçümlerinin yeni bir dış veri doğrulaması anlamına gelmez; makalede belirtilen veri kapsamı ve model sınırlılıkları geçerlidir.')

    newpage(d,'Teslim edilen dosyalar ve çalıştırma')
    table(d,['Bileşen','İçerik'],[
        ['Python kaynak kodları','Türetilmiş girdiler, SF-AHP, beş MCDM yöntemi ve bütün deneyler'],
        ['Tablo ve şekiller','21 makale tablosu; 3 ana şekil; 3 ek görsel; dosya eşleştirmesi'],
        ['Monte Carlo kayıtları','5.000 ağırlık vektörü, yöntem sıraları, Borda ve konsensüs sıraları'],
        ['Supplementary Material','İngilizce yöntem, veri ve yeniden üretim belgesi'],
        ['Gönderim belgeleri','Cover Letter taslağı ve başlık sayfası'],
        ['Kullanım rehberi','GitHub yükleme, Actions, yerel Python ve Colab adımları'],
        ['Kaynak izlenebilirliği','Değiştirilmemiş çalışma kitabı, kaynak karşılaştırmaları ve dosya özetleri']],[2.15,4.55])
    paragraph(d,'Çalışma, ana makalenin kabul edilen sürümündeki sonuçlarla eşleştirilmiştir. Ana makalenin işaretli değişiklikleri ve Microsoft Equation nesneleri aynı dosyada korunur. Veri tabloları ve şekiller ayrıca Python kodundan üretilir; mimari şekil özgün dosyadan kopyalanır.')
    code(d,'python -m pip install -r requirements.txt\npython -m unittest discover -s tests -v\npython run_analysis.py\npython scripts/check_reproduction.py\npython scripts/build_supplement.py')
    paragraph(d,'Son kontrol, ZIP dosyasından yeni bir klasöre açılan proje üzerinde aynı komutlarla yapılır. Beklenen sonuç results/reproduction_check.json içinde PASS değeridir. Onaylanan makale dosyasının SHA-256 özeti manuscript/approved_identity.json içinde yer alır. SHA256SUMS, arşivdeki dosyaların bütünlük özetlerini içerir.')
    paragraph(d,'GitHub Actions iş akışı hazırlanmış ve adımlar yerel ortamda çalıştırılmıştır. Bu teslim sırasında GitHub hesabında depo oluşturulmamış ve iş akışı başlatılmamıştır. Yükleme ve çalıştırma işlemleri GitHub_Kullanim_Rehberi belgesinde adım adım açıklanmıştır.')
    path=ROOT/'docs/Kontrol_Raporu.docx';d.save(path);return path

def main():
    paths=[build_supplement(ROOT)]
    guide=markdown_document((ROOT/'docs/github_tr.md').read_text(),'GitHub yükleme ve çalıştırma rehberi',('4 ','7 ','10 '))
    guide_path=ROOT/'docs/GitHub_Kullanim_Rehberi.docx';guide.save(guide_path);paths.append(guide_path)
    paths.extend([cover(),audit()])
    for path in paths:print(path)

if __name__=='__main__':main()
