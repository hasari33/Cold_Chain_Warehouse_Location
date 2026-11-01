# GitHub yükleme ve çalıştırma rehberi

Bu rehber, Cold_Chain_Warehouse_Location paketinin tamamını GitHub'a yüklemenizi, analizleri GitHub Actions üzerinde çalıştırmanızı ve sonuçları indirmenizi sağlar. Onaylanan makalenin sonuçları için varsayılan ayarları kullanın. Python kodunu GitHub'a yüklemek tek başına çalıştırmaz; aşağıdaki Actions adımı hesaplamaları başlatır.

## 1 ZIP dosyasını açın

Cold_Chain_Warehouse_Location.zip dosyasına sağ tıklayın ve Tümünü Ayıkla seçeneğini kullanın. İçteki Cold_Chain_Warehouse_Location klasörünü açın. run_analysis.py, requirements.txt, README.md, data, src, scripts, reference_results ve .github aynı düzeyde bulunmalıdır. Yüklenecek içerik bu iç klasörün içeriğidir.

## 2 Boş bir depo oluşturun

GitHub hesabınıza girin. Sağ üstteki artı menüsünden New repository seçeneğini açın. Repository name alanına Cold_Chain_Warehouse_Location yazın. Görünürlüğü seçin. Boş depo elde etmek için Add a README file, .gitignore ve lisans ekleme seçeneklerini işaretlemeyin. Create repository düğmesine basın. Depo adresini kopyalayın.

## 3 Bütün dosyaları Git ile yükleyin

Git for Windows kuruluysa, ayıklanan iç klasörde sağ tıklayıp Open Git Bash here seçeneğini açın. Aşağıdaki komutları sırayla çalıştırın. KULLANICI_ADINIZ bölümünü gerçek GitHub kullanıcı adınızla değiştirin. Bu işlemde dosyaların tek tek yüklenmesi gerekmez ve .github klasörü de dahil edilir.

```bash
git init
git add .
git commit -m "Add reproducible cold-chain study"
git branch -M main
git remote add origin https://github.com/KULLANICI_ADINIZ/Cold_Chain_Warehouse_Location.git
git push -u origin main
```

Git ilk kullanımda ad ve e-posta isterse hesabınızda kullandığınız bilgileri girin ve commit komutunu tekrarlayın:

```bash
git config user.name "Hüseyin Ali Sarıkaya"
git config user.email "GITHUB_HESABINIZDAKI_EPOSTA"
```

GitHub kimlik doğrulaması açılırsa tarayıcıdaki hesabınızla giriş yapın. İşlem sonunda depo ana sayfasında run_analysis.py ve requirements.txt doğrudan görünmelidir. Klasör bir kez daha iç içe görünüyorsa Actions yanlış dizinde çalışır; içerik depo kökünde olmalıdır.

## 4 Tarayıcıdan yükleme seçeneği

Boş deponun ilk ekranında uploading an existing file bağlantısına tıklayın. Dosya listesi oluştuğunda sağ üstteki Add file menüsünde Upload files bulunur. Önce kök dosyaları ve sonra klasörleri aynı depo köküne yükleyebilirsiniz. Bir kerede en fazla 100 dosya seçin; büyük klasörleri birkaç işlemde yükleyin. Her işlemde Commit changes seçeneğini tamamlayın.

ZIP dosyasını tek dosya olarak yüklemek çalışır bir proje oluşturmaz. Ayıklanan dosyalar yüklenmelidir. Windows'ta nokta ile başlayan .github klasörü görünmüyorsa Dosya Gezgini'nde gizli öğeleri gösterin. Tarayıcı bu klasörü atladıysa Add file → Create new file ile .github/workflows/reproduce.yml yolunu oluşturun ve paketteki aynı dosyanın içeriğini yapıştırın. Commit changes ile kaydedin. İş akışının dosya yolu tam olarak bu olmalıdır.

## 5 GitHub Actions ile çalıştırın

Depodaki Actions sekmesini açın. İlk kullanımda görünen etkinleştirme seçeneğini onaylayın. Solda Reproduce manuscript results iş akışını seçin. Sağdaki Run workflow menüsünde main dalını seçip Run workflow düğmesine basın. Yeni çalıştırmayı açın ve reproduce görevine girin.

Sırasıyla bağımlılık kurulumu, sekiz bağımsız sayısal test, ana analiz, makale ve referans karşılaştırması, Supplementary Material belgesinin üretimi ve çıktıların saklanması adımlarını görürsünüz. Başarılı adımlar yeşil işaret alır. Yükleme sonrasında otomatik başlayan bir çalıştırma varsa onu da izleyebilirsiniz.

## 6 Sonuçları indirin

Tamamlanan çalıştırmanın özet sayfasına dönün. Artifacts bölümündeki cold-chain-reproduced-results öğesini indirin. results içindeki tablolar, ara hesaplamalar, Monte Carlo kayıtları ve şekiller ile Supplementary_Material.docx bu arşivde bulunur. Çıktılar bu iş akışında 30 gün saklanır; kalıcı olarak saklamak istediklerinizi indirin.

results/reproduction_check.json dosyasında status alanı PASS olmalıdır. Beklenen kontroller: 51 CSV, 21 makale tablosu, 2.026 tablo hücresi ve özgün mimari şeklin birebir korunması. Sayısal şekillerin piksel karşılaştırması farklı işletim sistemlerindeki yazı tipleri nedeniyle değişebilir; tablo değerlerinin eşleşmesi ayrıca kontrol edilir.

## 7 Windows bilgisayarda çalıştırın

Python 3.12 kurun. Proje klasöründe Komut İstemi açın. Sanal ortamı etkinleştirmeden kendi Python dosyasını kullanmak, PowerShell etkinleştirme engellerini önler:

```text
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe run_analysis.py
.venv\Scripts\python.exe scripts\check_reproduction.py
.venv\Scripts\python.exe scripts\build_supplement.py
```

Sonuçlar aynı klasördeki results dizinine yazılır. Bağımlılıklar kurulduktan sonra analiz internet istemez. Makaledeki 5.000 tekrar için --simulations seçeneğini değiştirmeniz gerekmez.

## 8 macOS veya Linux bilgisayarda çalıştırın

Proje klasöründe Terminal açıp aşağıdaki komutları çalıştırın:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python run_analysis.py
.venv/bin/python scripts/check_reproduction.py
.venv/bin/python scripts/build_supplement.py
```

## 9 Google Colab seçeneği

Paketteki notebooks/Reproduce_Cold_Chain.ipynb dosyasını Google Colab'a yükleyin. Hücreleri sırayla çalıştırın. Klasör bulunamazsa ilk kod hücresi sizden aynı ZIP dosyasını seçmenizi ister. Son hücre üretilen sonuçları ZIP olarak indirir. Bu seçenek için GitHub deposu yayımlanmış olmak zorunda değildir.

## 10 Çıktıları makaleyle eşleştirin

results/tables/table_01.csv ile table_14.csv, ana metnin 1–14 numaralı tablolarıdır. table_A1.csv, table_B1.csv–table_B5.csv ve table_C1.csv makalenin ek tablolarıdır. results/figures/figure_01_workflow.png özgün mimari şekildir; figure_02_method_ranks ve figure_03_rank_agreement ana makalenin diğer iki şeklidir. S1–S3 dosyaları ek görsellerdir. Ayrıntılı eşleştirme docs/artifact_map.csv içindedir.

Beklenen Borda sıralaması Etimesgut 8, Yenimahalle 12, Mamak 16'dır. İlk sıra olasılıkları sırasıyla %62,34, %37,62 ve %0,04'tür. Kendall W değeri 0,9071428571 olmalıdır. Makale aynı zamanda practitioners bilgisi ve özgün mimari şekliyle manuscript klasöründe korunmuştur.

## 11 Sık karşılaşılan sorunlar

No such file or directory mesajı, komutun proje kökünde çalışmadığını gösterir. Önce run_analysis.py dosyasının bulunduğu klasöre geçin. ModuleNotFoundError durumunda requirements.txt kurulumunu aynı Python ile tekrarlayın. Actions görünmüyorsa Settings → Actions → General altında iş akışlarının etkinliğini kontrol edin. Run workflow düğmesi görünmüyorsa reproduce.yml dosyasının main dalında ve .github/workflows altında bulunduğunu doğrulayın.

PASS alınmıyorsa parameters.json, girdi dosyaları veya referans sonuçların değişip değişmediğine bakın. Farklı ayarlarla yapılan keşif çalışmaları varsayılan sonuçlarla aynı olmak zorunda değildir. Ayrı bir klasör kullanın: python run_analysis.py --output exploratory_results. results klasörünü silmek girdileri silmez; yeniden çalıştırma bu çıktıları üretir.

## 12 Sürümü kaydedin

GitHub Releases bölümünden v2.0.0 sürümünü oluşturup bu ZIP dosyasını ekleyebilirsiniz. Gerçek bir DOI edinildiğinde CITATION.cff ve makalenin veri/kod erişim beyanına ekleyin.

## Resmi başvuru bağlantıları

- Dosya yükleme: https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository
- GitHub Actions başlangıç: https://docs.github.com/en/actions/get-started/quickstart
- Python iş akışı: https://docs.github.com/en/actions/tutorials/build-and-test-code/python
- İş akışı çıktıları: https://github.com/actions/upload-artifact

Erişim tarihi 31 Ekim 2026. GitHub hesabında çalıştırma başlatılmamıştır.
