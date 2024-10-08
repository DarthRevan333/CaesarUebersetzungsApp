# CaesarUebersetzungsApp
Eine App für verschiedene Plattformen, primär Android, mit welcher man Übersetzungen und Textstellen aus Caesars ["De bello gallico"](https://de.wikipedia.org/wiki/De_bello_Gallico)(Buch 1-8) finden kann.

<img src="readme_front.png" alt="Picture of app" width="40%">

## Fortführung
Es bestehen keine Pläne, diese App in Zukunft weiterzuentwickeln.

Falls es dennoch dazu kommen sollte, wird es mit einem Umstieg auf Kotlin einhergehen, bei dem die im Moment auf Python basierte App und ihr momentane Code nicht mehr verwendet werden kann.

## APK Download
Die .apk Datei kann neben dem Download durch Github auch [hier](https://drive.google.com/file/d/1dpQpOXywXwFo9lQ9qOvHwIgJ4y0cFQ83/view?usp=sharing) heruntergeladen werden.

## Hinweise zur App
Bei der Suche mit der App wird der eingegebenen Zeichenfolge automatisch ein Leerzeichen vorangestellt um Verwechslungen zu vermeiden z.B. Suchbegriff: "at barbari" würde ansonsten auch "erat barbari" finden.
Ebenfalls werden alle vorangestellten und nachgestellten Leerzeichen (bis auf das automatisch vorangestellte) ignoriert bzw. entfernt.

Mit "Immer vollkommen ausweiten" kann eingestellt werden, ob, jedes mal wenn der Suchknopf gedrückt wird, auch automatisch alle Textstellen auf volle Größe ausgeweitet werden sollen.

Mit "Parallele Ladebegrenzung" ist die Anzahl der maximal gleichzeitg zu ladenden Ergebnisse gemeint. Bei mehr gefundenen Ergebnissen taucht ein Knopf "Mehr anzeigen" auf, mit welchem man mehr Ergebnisse laden kann.

Das erneute Laden der Daten kann auf mobilen Plattformen einige Sekunden dauern und ist daher nicht zu empfehlen.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
