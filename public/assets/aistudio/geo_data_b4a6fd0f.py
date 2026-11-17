"""
DATABASE GEOGRAFICO COMPLETO ITALIA — CASALAVOROPRO
===================================================
Contiene tutte le 20 Regioni italiane, le relative Province e i principali
comuni/poli territoriali per estendere la ricerca su scala provinciale o regionale.
Permette ricerche aggregate (es. 'Vicenza e provincia tutta', 'Padova e provincia', ecc.)
per raggiungere obiettivi elevati di lead (100, 200, 300 fino a 1000).
"""

# Mappatura gerarchica: Regione -> Provincia/Zona -> Lista comuni per ricerca estesa
ITALIA_GEO_DATABASE = {
    "Veneto": {
        "Vicenza e provincia (Tutta)": [
            "Vicenza", "Bassano del Grappa", "Schio", "Thiene", "Arzignano",
            "Montecchio Maggiore", "Valdagno", "Lonigo", "Marostica", "Dueville",
            "Malo", "Chiampo", "Sandrigo", "Creazzo", "Cornedo Vicentino", "Camisano Vicentino"
        ],
        "Padova e provincia (Tutta)": [
            "Padova", "Cittadella", "Abano Terme", "Monselice", "Piove di Sacco",
            "Este", "Albignasego", "Vigonza", "Selvazzano Dentro", "Rubano",
            "Campodarsego", "San Martino di Lupari", "Piazzola sul Brenta", "Montegrotto Terme"
        ],
        "Verona e provincia (Tutta)": [
            "Verona", "Villafranca di Verona", "Legnago", "San Bonifacio", "Bussolengo",
            "Negrar di Valpolicella", "Peschiera del Garda", "Cerea", "Bovolone", "Zevio",
            "Valeggio sul Mincio", "San Giovanni Lupatoto", "Grezzana"
        ],
        "Treviso e provincia (Tutta)": [
            "Treviso", "Conegliano", "Castelfranco Veneto", "Montebelluna", "Vittorio Veneto",
            "Mogliano Veneto", "Paese", "Oderzo", "Villorba", "Preganziol", "Roncade", "Pieve di Soligo"
        ],
        "Venezia e provincia (Tutta)": [
            "Venezia", "Mestre", "Chioggia", "San Donà di Piave", "Mira", "Spinea",
            "Mirano", "Jesolo", "Portogruaro", "Scorzè", "Santa Maria di Sala", "Marcon", "Noale"
        ],
        "Belluno e provincia (Tutta)": [
            "Belluno", "Feltre", "Sedico", "Ponte nelle Alpi", "Cortina d'Ampezzo",
            "Santa Giustina", "Mel", "Borgo Valbelluna", "Agordo"
        ],
        "Rovigo e provincia (Tutta)": [
            "Rovigo", "Adria", "Porto Viro", "Occhiobello", "Badia Polesine",
            "Lendinara", "Porto Tolle", "Taglio di Po"
        ],
        "Vicenza (Città)": ["Vicenza"],
        "Bassano del Grappa (Città)": ["Bassano del Grappa"],
        "Schio (Città)": ["Schio"],
        "Thiene (Città)": ["Thiene"],
        "Padova (Città)": ["Padova"],
        "Verona (Città)": ["Verona"],
        "Treviso (Città)": ["Treviso"],
        "Venezia (Città)": ["Venezia", "Mestre"]
    },
    "Lombardia": {
        "Milano e provincia (Tutta)": [
            "Milano", "Sesto San Giovanni", "Cinisello Balsamo", "Legnano", "Rho",
            "Paderno Dugnano", "Cologno Monzese", "Rozzano", "San Donato Milanese",
            "Abbiategrasso", "Segrate", "Bollate", "Pioltello", "San Giuliano Milanese"
        ],
        "Brescia e provincia (Tutta)": [
            "Brescia", "Desenzano del Garda", "Montichiari", "Lumezzane", "Palazzolo sull'Oglio",
            "Rovato", "Chiari", "Ghedi", "Manerbio", "Darfo Boario Terme", "Salò", "Iseo"
        ],
        "Bergamo e provincia (Tutta)": [
            "Bergamo", "Treviglio", "Seriate", "Dalmine", "Romano di Lombardia",
            "Albino", "Caravaggio", "Alzano Lombardo", "Stezzano", "Osio Sotto"
        ],
        "Monza e Brianza (Tutta)": [
            "Monza", "Lissone", "Seregno", "Desio", "Cesano Maderno",
            "Limbiate", "Brugherio", "Vimercate", "Giussano", "Muggiò", "Meda"
        ],
        "Varese e provincia (Tutta)": [
            "Varese", "Busto Arsizio", "Gallarate", "Saronno", "Cassano Magnago",
            "Somma Lombardo", "Tradate", "Malnate", "Castellanza"
        ],
        "Como e provincia (Tutta)": [
            "Como", "Cantù", "Mariano Comense", "Erba", "Olgiate Comasco", "Lurate Caccivio"
        ],
        "Pavia e provincia (Tutta)": [
            "Pavia", "Vigevano", "Voghera", "Mortara", "Stradella", "Garlasco", "Broni"
        ],
        "Cremona e provincia (Tutta)": [
            "Cremona", "Crema", "Casalmaggiore", "Castelleone", "Soresina", "Pandino"
        ],
        "Mantova e provincia (Tutta)": [
            "Mantova", "Castiglione delle Stiviere", "Suzzara", "Viadana", "Porto Mantovano", "Curtatone"
        ],
        "Lecco e provincia (Tutta)": [
            "Lecco", "Merate", "Calolziocorte", "Casatenovo", "Valmadrera"
        ],
        "Lodi e provincia (Tutta)": [
            "Lodi", "Codogno", "Casalpusterlengo", "Sant'Angelo Lodigiano"
        ],
        "Sondrio e provincia (Tutta)": [
            "Sondrio", "Morbegno", "Tirano", "Chiavenna", "Bormio"
        ]
    },
    "Piemonte": {
        "Torino e provincia (Tutta)": [
            "Torino", "Moncalieri", "Collegno", "Rivoli", "Nichelino", "Settimo Torinese",
            "Grugliasco", "Chieri", "Pinerolo", "Venaria Reale", "Carmagnola", "Ivrea"
        ],
        "Novara e provincia (Tutta)": ["Novara", "Borgomanero", "Trecate", "Arona", "Oleggio"],
        "Alessandria e provincia (Tutta)": ["Alessandria", "Casale Monferrato", "Novi Ligure", "Tortona", "Acqui Terme", "Valenza"],
        "Cuneo e provincia (Tutta)": ["Cuneo", "Alba", "Bra", "Fossano", "Mondovì", "Savigliano", "Saluzzo"],
        "Asti e provincia (Tutta)": ["Asti", "Canelli", "Nizza Monferrato", "San Damiano d'Asti"],
        "Biella e provincia (Tutta)": ["Biella", "Cossato", "Vigliano Biellese", "Candelo"],
        "Vercelli e provincia (Tutta)": ["Vercelli", "Borgosesia", "Santhià", "Gattinara"],
        "Verbano-Cusio-Ossola (Tutta)": ["Verbania", "Domodossola", "Omegna", "Gravellona Toce"]
    },
    "Emilia-Romagna": {
        "Bologna e provincia (Tutta)": [
            "Bologna", "Imola", "Casalecchio di Reno", "San Lazzaro di Savena",
            "Valsamoggia", "San Giovanni in Persiceto", "Castel San Pietro Terme", "Zola Predosa"
        ],
        "Modena e provincia (Tutta)": ["Modena", "Carpi", "Sassuolo", "Formigine", "Castelfranco Emilia", "Vignola", "Mirandola"],
        "Reggio Emilia e provincia (Tutta)": ["Reggio Emilia", "Correggio", "Scandiano", "Casalgrande", "Guastalla", "Castellarano"],
        "Parma e provincia (Tutta)": ["Parma", "Fidenza", "Salsomaggiore Terme", "Collecchio", "Noceto", "Montechiarugolo"],
        "Ravenna e provincia (Tutta)": ["Ravenna", "Faenza", "Lugo", "Cervia", "Bagnacavallo", "Russi"],
        "Ferrara e provincia (Tutta)": ["Ferrara", "Cento", "Comacchio", "Argenta", "Copparo", "Bondeno"],
        "Forlì-Cesena (Tutta)": ["Forlì", "Cesena", "Cesenatico", "Savignano sul Rubicone", "Forlimpopoli"],
        "Rimini e provincia (Tutta)": ["Rimini", "Riccione", "Santarcangelo di Romagna", "Bellaria-Igea Marina", "Cattolica"],
        "Piacenza e provincia (Tutta)": ["Piacenza", "Fiorenzuola d'Arda", "Castel San Giovanni", "Rottofreno", "Podenzano"]
    },
    "Toscana": {
        "Firenze e provincia (Tutta)": [
            "Firenze", "Scandicci", "Sesto Fiorentino", "Empoli", "Campi Bisenzio",
            "Bagno a Ripoli", "Fucecchio", "Pontassieve", "Lastra a Signa", "Figline e Incisa Valdarno"
        ],
        "Prato e provincia (Tutta)": ["Prato", "Montemurlo", "Carmignano", "Poggio a Caiano", "Vaiano"],
        "Pisa e provincia (Tutta)": ["Pisa", "Cascina", "San Giuliano Terme", "Pontedera", "San Miniato", "Ponsacco"],
        "Livorno e provincia (Tutta)": ["Livorno", "Piombino", "Rosignano Marittimo", "Cecina", "Collesalvetti"],
        "Arezzo e provincia (Tutta)": ["Arezzo", "Montevarchi", "Cortona", "San Giovanni Valdarno", "Sansepolcro"],
        "Pistoia e provincia (Tutta)": ["Pistoia", "Montecatini Terme", "Quarrata", "Monsummano Terme", "Pescia"],
        "Lucca e provincia (Tutta)": ["Lucca", "Viareggio", "Capannori", "Camaiore", "Pietrasanta", "Massarosa"],
        "Siena e provincia (Tutta)": ["Siena", "Poggibonsi", "Colle di Val d'Elsa", "Montepulciano", "Sinalunga"],
        "Grosseto e provincia (Tutta)": ["Grosseto", "Follonica", "Orbetello", "Monte Argentario", "Castiglione della Pescaia"],
        "Massa-Carrara (Tutta)": ["Massa", "Carrara", "Aulla", "Montignoso", "Fivizzano"]
    },
    "Lazio": {
        "Roma e provincia (Tutta)": [
            "Roma", "Guidonia Montecelio", "Fiumicino", "Pomezia", "Tivoli", "Anzio",
            "Velletri", "Civitavecchia", "Nettuno", "Ardea", "Ciampino", "Albano Laziale",
            "Marino", "Monterotondo", "Ladispoli", "Cerveteri", "Frascati", "Colleferro"
        ],
        "Latina e provincia (Tutta)": ["Latina", "Aprilia", "Terracina", "Formia", "Cisterna di Latina", "Fondi", "Gaeta", "Sezze"],
        "Frosinone e provincia (Tutta)": ["Frosinone", "Cassino", "Alatri", "Sora", "Ceccano", "Anagni", "Ferentino"],
        "Viterbo e provincia (Tutta)": ["Viterbo", "Civita Castellana", "Tarquinia", "Vetralla", "Montefiascone"],
        "Rieti e provincia (Tutta)": ["Rieti", "Fara in Sabina", "Cittaducale", "Poggio Mirteto"]
    },
    "Campania": {
        "Napoli e provincia (Tutta)": [
            "Napoli", "Giugliano in Campania", "Torre del Greco", "Pozzuoli", "Casoria",
            "Castellammare di Stabia", "Afragola", "Marano di Napoli", "Portici", "Ercolano",
            "Acerra", "Casalnuovo di Napoli", "San Giorgio a Cremano", "Torre Annunziata", "Pomigliano d'Arco", "Nola"
        ],
        "Salerno e provincia (Tutta)": ["Salerno", "Cava de' Tirreni", "Battipaglia", "Nocera Inferiore", "Scafati", "Eboli", "Pagani", "Angri", "Sarno"],
        "Caserta e provincia (Tutta)": ["Caserta", "Aversa", "Marcianise", "Maddaloni", "Santa Maria Capua Vetere", "Mondragone", "Orta di Atella"],
        "Avellino e provincia (Tutta)": ["Avellino", "Ariano Irpino", "Montoro", "Solofra", "Mercogliano", "Atripalda"],
        "Benevento e provincia (Tutta)": ["Benevento", "Montesarchio", "San Giorgio del Sannio", "Sant'Agata de' Goti"]
    },
    "Puglia": {
        "Bari e provincia (Tutta)": [
            "Bari", "Altamura", "Molfetta", "Bitonto", "Monopoli", "Corato",
            "Gravina in Puglia", "Modugno", "Gioia del Colle", "Triggiano", "Terlizzi", "Putignano"
        ],
        "Taranto e provincia (Tutta)": ["Taranto", "Martina Franca", "Massafra", "Grottaglie", "Manduria", "Castellaneta"],
        "Foggia e provincia (Tutta)": ["Foggia", "Cerignola", "Manfredonia", "San Severo", "Lucera", "San Giovanni Rotondo"],
        "Lecce e provincia (Tutta)": ["Lecce", "Nardò", "Galatina", "Copertino", "Gallipoli", "Casarano", "Maglie"],
        "Brindisi e provincia (Tutta)": ["Brindisi", "Fasano", "Francavilla Fontana", "Ostuni", "Mesagne", "Ceglie Messapica"],
        "Barletta-Andria-Trani (Tutta)": ["Andria", "Barletta", "Trani", "Bisceglie", "Canosa di Puglia"]
    },
    "Sicilia": {
        "Palermo e provincia (Tutta)": ["Palermo", "Bagheria", "Carini", "Monreale", "Partinico", "Termini Imerese", "Misilmeri", "Villabate"],
        "Catania e provincia (Tutta)": ["Catania", "Acireale", "Misterbianco", "Paternò", "Caltagirone", "Adrano", "Gravina di Catania", "Giarre"],
        "Messina e provincia (Tutta)": ["Messina", "Barcellona Pozzo di Gotto", "Milazzo", "Patti", "Capo d'Orlando", "Taormina"],
        "Siracusa e provincia (Tutta)": ["Siracusa", "Augusta", "Avola", "Noto", "Floridia", "Lentini"],
        "Trapani e provincia (Tutta)": ["Trapani", "Marsala", "Mazara del Vallo", "Alcamo", "Castelvetrano", "Erice"],
        "Ragusa e provincia (Tutta)": ["Ragusa", "Vittoria", "Modica", "Comiso", "Scicli", "Pozzallo"],
        "Agrigento e provincia (Tutta)": ["Agrigento", "Sciacca", "Licata", "Canicattì", "Favara", "Palma di Montechiaro"],
        "Caltanissetta e provincia (Tutta)": ["Caltanissetta", "Gela", "Niscemi", "San Cataldo", "Mazzarino"],
        "Enna e provincia (Tutta)": ["Enna", "Piazza Armerina", "Nicosia", "Leonforte", "Barrafranca"]
    },
    "Liguria": {
        "Genova e provincia (Tutta)": ["Genova", "Rapallo", "Chiavari", "Sestri Levante", "Lavagna", "Arenzano", "Recco"],
        "La Spezia e provincia (Tutta)": ["La Spezia", "Sarzana", "Arcola", "Lerici", "Santo Stefano di Magra"],
        "Savona e provincia (Tutta)": ["Savona", "Albenga", "Varazze", "Cairo Montenotte", "Finale Ligure", "Loano"],
        "Imperia e provincia (Tutta)": ["Sanremo", "Imperia", "Ventimiglia", "Taggia", "Bordighera"]
    },
    "Friuli-Venezia Giulia": {
        "Udine e provincia (Tutta)": ["Udine", "Codroipo", "Tavagnacco", "Latisana", "Cervignano del Friuli", "Cividale del Friuli", "Gemona del Friuli"],
        "Pordenone e provincia (Tutta)": ["Pordenone", "Sacile", "Cordenons", "Azzano Decimo", "Porcia", "San Vito al Tagliamento"],
        "Trieste e provincia (Tutta)": ["Trieste", "Muggia", "Duino-Aurisina", "San Dorligo della Valle"],
        "Gorizia e provincia (Tutta)": ["Gorizia", "Monfalcone", "Ronchi dei Legionari", "Gradisca d'Isonzo"]
    },
    "Trentino-Alto Adige": {
        "Trento e provincia (Tutta)": ["Trento", "Rovereto", "Pergine Valsugana", "Arco", "Riva del Garda", "Mori"],
        "Bolzano e provincia (Tutta)": ["Bolzano", "Merano", "Bressanone", "Brunico", "Laives", "Appiano sulla Strada del Vino"]
    },
    "Marche": {
        "Ancona e provincia (Tutta)": ["Ancona", "Senigallia", "Jesi", "Fabriano", "Falconara Marittima", "Osimo", "Castelfidardo"],
        "Pesaro e Urbino (Tutta)": ["Pesaro", "Fano", "Urbino", "Vallefoglia", "Mondolfo", "Colli al Metauro"],
        "Macerata e provincia (Tutta)": ["Macerata", "Civitanova Marche", "Recanati", "Tolentino", "Potenza Picena", "Corridonia"],
        "Ascoli Piceno e provincia (Tutta)": ["Ascoli Piceno", "San Benedetto del Tronto", "Grottammare", "Monteprandone", "Folignano"],
        "Fermo e provincia (Tutta)": ["Fermo", "Porto Sant'Elpidio", "Sant'Elpidio a Mare", "Porto San Giorgio", "Montegranaro"]
    },
    "Abruzzo": {
        "Pescara e provincia (Tutta)": ["Pescara", "Montesilvano", "Spoltore", "Città Sant'Angelo", "Penne", "Cepagatti"],
        "Chieti e provincia (Tutta)": ["Chieti", "Vasto", "Lanciano", "Francavilla al Mare", "Ortona", "San Salvo"],
        "Teramo e provincia (Tutta)": ["Teramo", "Roseto degli Abruzzi", "Giulianova", "Silvi", "Pineto", "Alba Adriatica"],
        "L'Aquila e provincia (Tutta)": ["L'Aquila", "Avezzano", "Sulmona", "Celano", "Pratola Peligna"]
    },
    "Sardegna": {
        "Cagliari e provincia (Tutta)": ["Cagliari", "Quartu Sant'Elena", "Selargius", "Assemini", "Capoterra", "Sestu", "Monserrato"],
        "Sassari e provincia (Tutta)": ["Sassari", "Olbia", "Alghero", "Porto Torres", "Tempio Pausania", "Arzachena", "Sorso"],
        "Nuoro e provincia (Tutta)": ["Nuoro", "Siniscola", "Macomer", "Dorgali", "Orosei"],
        "Oristano e provincia (Tutta)": ["Oristano", "Terralba", "Cabras", "Bosa", "Marrubiu"],
        "Sud Sardegna (Tutta)": ["Carbonia", "Iglesias", "Villacidro", "Guspini", "Sant'Antioco"]
    },
    "Umbria": {
        "Perugia e provincia (Tutta)": ["Perugia", "Foligno", "Città di Castello", "Spoleto", "Gubbio", "Assisi", "Bastia Umbra", "Marsciano", "Todi"],
        "Terni e provincia (Tutta)": ["Terni", "Orvieto", "Narni", "Amelia", "Montecastrilli"]
    },
    "Calabria": {
        "Cosenza e provincia (Tutta)": ["Cosenza", "Corigliano-Rossano", "Rende", "Castrovillari", "Acri", "Montalto Uffugo"],
        "Reggio Calabria e provincia (Tutta)": ["Reggio Calabria", "Gioia Tauro", "Palmi", "Siderno", "Taurianova", "Rosarno"],
        "Catanzaro e provincia (Tutta)": ["Catanzaro", "Lamezia Terme", "Soverato", "Sellia Marina", "Borgia"],
        "Crotone e provincia (Tutta)": ["Crotone", "Isola di Capo Rizzuto", "Cirò Marina", "Cutro", "Petilia Policastro"],
        "Vibo Valentia e provincia (Tutta)": ["Vibo Valentia", "Pizzo", "Mileto", "Serra San Bruno", "Tropea"]
    },
    "Basilicata": {
        "Potenza e provincia (Tutta)": ["Potenza", "Melfi", "Lavello", "Rionero in Vulture", "Lauria", "Venosa", "Avigliano"],
        "Matera e provincia (Tutta)": ["Matera", "Pisticci", "Policoro", "Bernalda", "Montescaglioso", "Scanzano Jonico"]
    },
    "Molise": {
        "Campobasso e provincia (Tutta)": ["Campobasso", "Termoli", "Bojano", "Campomarino", "Larino", "Guglionesi"],
        "Isernia e provincia (Tutta)": ["Isernia", "Venafro", "Agnone", "Frosolone"]
    },
    "Valle d'Aosta": {
        "Valle d'Aosta (Tutta)": ["Aosta", "Saint-Vincent", "Châtillon", "Sarre", "Pont-Saint-Martin", "Gressan", "Courmayeur"]
    }
}


def get_all_regions() -> list[str]:
    """Ritorna la lista in ordine delle 20 Regioni italiane."""
    return list(ITALIA_GEO_DATABASE.keys())


def get_zones_for_region(region: str) -> list[str]:
    """Ritorna l'elenco delle province e città disponibili per la regione indicata."""
    if region in ITALIA_GEO_DATABASE:
        return list(ITALIA_GEO_DATABASE[region].keys())
    return []


def resolve_search_locations(region: str, zone_or_city: str) -> list[str]:
    """
    Risolve una selezione territoriale in una sequenza ordinata di città/comuni
    da esplorare per raggiungere il limite desiderato (anche 500 o 1000 lead).
    
    Esempio:
      resolve_search_locations('Veneto', 'Vicenza e provincia (Tutta)')
      -> ['Vicenza', 'Bassano del Grappa', 'Schio', 'Thiene', 'Arzignano', ...]
    """
    if not zone_or_city:
        zone_or_city = "Vicenza e provincia (Tutta)"
        region = "Veneto"

    # Se la zona corrisponde esattamente a una chiave nel database regionale
    if region in ITALIA_GEO_DATABASE and zone_or_city in ITALIA_GEO_DATABASE[region]:
        return ITALIA_GEO_DATABASE[region][zone_or_city]

    # Cerca la chiave in qualsiasi regione (ricerca flessibile)
    for reg, zones in ITALIA_GEO_DATABASE.items():
        if zone_or_city in zones:
            return zones[zone_or_city]

    # Se è una stringa libera (es. "Bassano del Grappa" o "Lonigo")
    return [zone_or_city.strip()]
