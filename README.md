# Railway-Cursor Bridge

Een geautomatiseerd systeem voor het detecteren en oplossen van Railway deployment fouten met behulp van Cursor IDE.

## Overzicht

De Railway-Cursor Bridge maakt een naadloze verbinding tussen Railway deployments en de Cursor IDE. Wanneer een deployment op Railway faalt, wordt automatisch:

1. De fout gedetecteerd via polling of webhooks
2. De logs geanalyseerd om specifieke fouten te identificeren
3. Een AI-prompt met specifieke instructies gegenereerd
4. Cursor geopend met het repository en de AI-prompt
5. De AI in Cursor voorgesteld om het probleem op te lossen

## Componenten

Dit pakket bevat de volgende componenten:

- **cursor_bridge.py**: Basis versie die periodiek Railway deployment status poll
- **cursor_bridge_enhanced.py**: Uitgebreide versie met desktopnotificaties
- **cursor_bridge_notification.py**: Helper voor systeemnotificaties
- **webhook_server.py**: Webhook server voor directe Railway notificaties
- **test_cursor_bridge.py**: Testscript voor lokale logbestanden

## Vereisten

- Python 3.6 of hoger
- Cursor IDE geïnstalleerd op je lokale machine
- Railway API token
- GitHub repository met je code
- (Optioneel) GitHub token voor het automatisch committen van wijzigingen

## Installatie

Gebruik het `install.sh` script om de Railway-Cursor Bridge te installeren:

```bash
./install.sh
```

Dit script zal:
1. Een Python virtual environment aanmaken
2. De benodigde dependencies installeren
3. De scripts uitvoerbaar maken
4. Je vragen om configuratie-informatie
5. Voor macOS een launchd service configureren

## Configuratie

Je kunt de bridge configureren via omgevingsvariabelen of door de configuratie in het `.env` bestand op te slaan:

```
RAILWAY_TOKEN=<jouw railway api token>
GITHUB_TOKEN=<jouw github token>
GITHUB_REPO=<gebruikersnaam/repo>
RAILWAY_PROJECT_ID=<jouw railway project id>
LOCAL_REPO_PATH=<pad naar lokale repository>
POLL_INTERVAL_SECONDS=60
```

## Gebruik

### Achtergrondservice

De Bridge kan als een achtergrondservice draaien om continu Railway deployment status te monitoren:

```bash
python3 cursor_bridge_enhanced.py
```

### Webhook Server

Je kunt ook de webhook server starten om directe notificaties van Railway te ontvangen:

```bash
python3 webhook_server.py
```

Configureer vervolgens een webhook in Railway met URL: `http://jouw-server:8080/webhook`

### Handmatig Testen

Voor het testen met een lokaal log bestand:

```bash
python3 test_cursor_bridge.py --log-file JOUW_LOGBESTAND.txt --repo-path PAD_NAAR_REPO
```

## Werking

1. **Detectie**: De bridge detecteert gefaalde deployments via Railway API of webhook
2. **Analyse**: De deployment logs worden geanalyseerd om fouten te identificeren
3. **Prompt Generatie**: Er worden twee bestanden gegenereerd:
   - Een AI-prompt bestand met specifieke instructies
   - Een foutdetailbestand met de logs en analyse
4. **Cursor Activatie**: Cursor wordt geopend met het repository en beide bestanden
5. **AI Oplossing**: De AI in Cursor krijgt direct de instructie om de fout te analyseren en op te lossen
6. **Commit & Push**: Na het oplossen kan de AI de wijzigingen committen en pushen
7. **Redeploy**: Railway zal automatisch opnieuw deployen na de push

## Voordelen

- **Instant Response**: Zodra een deployment faalt, wordt Cursor gestart
- **Gestructureerde Oplossing**: De AI krijgt duidelijke instructies over de fout
- **Volledig Geautomatiseerd**: Minimale handmatige interventie vereist
- **Volledige Context**: De AI krijgt zowel de foutdetails als toegang tot de code

## Problemen Oplossen

Als je problemen ondervindt:

- Controleer de logbestanden in `cursor_bridge_error.log` en `cursor_bridge_output.log`
- Zorg dat de Railway API token geldig is
- Controleer of het pad naar de Cursor executable correct is
- Verifieer dat het repository pad geldig is

## Licentie

Dit project is gelicenseerd onder de MIT Licentie. 