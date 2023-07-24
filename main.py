import requests
from bs4 import BeautifulSoup
from threading import Thread
from time import sleep
from requests.adapters import HTTPAdapter
from kivymd.app import MDApp
from kivymd.uix.card import MDSeparator
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.chip import MDChip
from kivymd.uix.button import MDIconButton, MDFlatButton, MDRectangleFlatIconButton
from kivy.uix.widget import Widget
from kivy.storage.jsonstore import JsonStore
from kivy.clock import Clock, mainthread


class LateinScraper:
    def __init__(self):
        self.src_address_base = "https://www.gottwein.de/Lat/caes/"
        self.targets_src = "https://www.gottwein.de/Lat/caes/caes001.php"
        self.targets = []
        self.headers = {
            'authority': 'www.gottwein.de',
            'accept': 'text/html',
            'accept-language': 'en-US,en;q=0.9',
            'dnt': '1',
            'accept-encoding': 'gzip, deflate, br',
            'referer': 'https://www.google.de',
            'sec-ch-ua': '"Opera GX";v="99", "Chromium";v="113", "Not-A.Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'no-cors',
            'sec-fetch-site': 'cross-site',
            'sec-fetch-user': '?1',
            'sec-gpc': '1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 OPR/99.0.0.0',
        }
        self.session = None
        self.__thread_return_data = []
        self.data = [[], []]
        self.translation_dict = {"10": "Erstes Buch", "20": "Zweites Buch", "30": "Drittes Buch", "40": "Viertes Buch", "50":
                     "Fünftes Buch", "60": "Sechtes Buch", "70": "Siebtes Buch", "80": "Achtes Buch"}
        self.adapter = HTTPAdapter(pool_connections=36, pool_maxsize=36)

    def update_targets(self) -> None:
        if self.session is None:
            self.session = requests.session()
            self.session.mount("http://", self.adapter)
            self.session.mount("https://", self.adapter)
        response = self.session.get(self.targets_src, headers=self.headers)
        soup = BeautifulSoup(response.text, "html.parser")
        self.targets.extend([r.attrs["value"] for r in soup.find_all("option") if not r.has_attr("selected") and
                             "CaesbGI" not in r.attrs["value"]])

    def __thread_scraping_func(self, target: str) -> None:
        soup = BeautifulSoup(self.session.get(f"{self.src_address_base}{target}", headers=self.headers).text, "html.parser")
        while soup.text.strip().startswith("The page is temporarily unavailable"):
            sleep(0.05)
            soup = BeautifulSoup(self.session.get(f"{self.src_address_base}{target}", headers=self.headers).text, "html.parser")
        self.__thread_return_data.append([target, zip([t.text.replace("\xa0", " ") for t in soup.find_all("div", attrs={"class": "zl"})], [t.text.replace("\xa0", " ") for t in soup.find_all("div", attrs={"class": "zr"})])])

    def update_data(self, store: JsonStore = None) -> None:
        if not self.targets:
            self.update_targets()
        if self.session is None:
            self.session = requests.session()
            self.session.mount("http://", self.adapter)
            self.session.mount("https://", self.adapter)
        for delay_counter, target in enumerate(self.targets):
            Thread(target=self.__thread_scraping_func, args=(target,)).start()
            if delay_counter % 2:
                sleep(0.035)
        while len(self.__thread_return_data) < 35:
            sleep(0.1)
        self.__thread_return_data.sort(key=lambda x: self.targets.index(x[0]))
        for title, chunk in self.__thread_return_data:
            self.data[0].append(title)
            self.data[1].append(list(chunk))
        self.__thread_return_data.clear()
        if store is not None:
            store.put("data", data=self.data)

    def search_in_data(self, substr: str, ignore_case: bool = True) -> list:
        found = []
        if not substr.startswith(" "):
            substr = f" {substr}"
        if ignore_case:
            substr = substr.lower()
            for chunk_num, chunks in enumerate(self.data[1]):
                for i, chunk in enumerate(chunks):
                    if (i2 := (" " + chunk[0]).lower().find(substr)) > -1:
                        found.append([chunk_num, i, i2])
        else:
            for chunk_num, chunks in enumerate(self.data[1]):
                for i, chunk in enumerate(chunks):
                    if (i2 := (" " + chunk[0]).find(substr)) > -1:
                        found.append([chunk_num, i, i2])
        return found

    def get_from_data(self, found_index_list: list, formatted: bool = True) -> list:
        if not formatted:
            return [self.data[1][found_index_list[0]][found_index_list[1]][0], self.data[1][found_index_list[0]][found_index_list[1]][1]]
        else:
            return self.format_chunk(self.data[1][found_index_list[0]][found_index_list[1]])

    def get_from_substr(self, substr: str, ignore_case: bool = True, formatted: bool = True, title_return: bool = False) -> list:
        final = []
        titles = []
        sr = self.search_in_data(substr, ignore_case=ignore_case)
        for s in sr:
            final.append(self.get_from_data(s, formatted=formatted))
            if title_return:
                titles.append(self.title_from_data(s))

        seen = []
        to_remove = []
        for i, sublist in enumerate(final):
            if sublist not in seen:
                seen.append(sublist)
            else:
                to_remove.append(i)
        final = seen
        titles = [title for i, title in enumerate(titles) if i not in to_remove]

        if title_return:
            return [titles, final]
        else:
            return final

    def title_from_data(self, found_index_list: list) -> str:
        return self.translate_title(self.data[0][found_index_list[0]])

    def translate_title(self, title: str) -> str:
        for k, v in self.translation_dict.items():
            if title.startswith(f"bg{k}"):
                return v

    @staticmethod
    def format_chunk(chunk: list) -> list[list[str], list[str]]:
        nchunk = [[], []]
        for i, text in enumerate(chunk):
            num = 2
            nchunk[i].append(text[:text.find("(2)")])
            while True:
                num_start = f"({num})"
                num_end = f"({num + 1})"
                if num_start in text:
                    if num_end in text:
                        nchunk[i].append(text[text.find(num_start):text.find(num_end)].strip())
                    else:
                        nchunk[i].append(text[text.find(num_start):].strip())
                    num += 1
                else:
                    break
        return nchunk

    def check_data(self, store: JsonStore, load_from_store: bool = True) -> bool:
        if store.exists("data") and store.get("data") is not None and load_from_store:
            self.data = store.get("data").get("data")
        else:
            if self.check_for_connection():
                if not load_from_store:
                    self.data = [[], []]
                self.update_data(store=store)
            else:
                return False
        return True

    @staticmethod
    def check_for_connection() -> bool:
        try:
            r = requests.head("https://google.de", timeout=1.5)
            r.raise_for_status()
            return True
        except Exception:
            return False


class CLabel(MDLabel):
    def __init__(self, **kwargs):
        if "on_kv_post" in kwargs.keys():
            self.on_render = kwargs.pop("on_kv_post")
        else:
            self.on_render = None
        self.texture_updated = False
        super().__init__(**kwargs)

    def on_parent(self, *_) -> None:
        if self.on_render is not None:
            if self.texture_updated:
                Clock.schedule_once(lambda *_: self.on_render(client_call=True))
            else:
                Clock.schedule_once(self.on_parent, 0.05)

    def on_texture_size(self, *_) -> None:
        if self.on_render is not None:
            if not self.texture_updated:
                self.texture_updated = True


class SettingsChip(MDChip):
    def on_long_touch(self, *args) -> None:
        pass


class HeaderLabel(MDLabel):
    pass


class TLayout(MDBoxLayout):
    pass


class TranslationLayout(MDBoxLayout):
    def __init__(self, text: list, text2: list, always_expanding: bool, *args, header_text: str = None, update: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.current = []
        self.before = []
        self.after = []
        self.updating_next = False
        self.last_pos_update = None
        if not always_expanding:
            self.process_text(text, text2)
            self.L1 = CLabel(text=self.current[0], pos_hint={"bottom": 0}, on_kv_post=self.update_pos if not update else Client.update_texts_pos)
            self.L2 = CLabel(text=self.current[1], pos_hint={"bottom": 0})
            self.Ubtn = False
            self.Dbtn = False
            if self.before:
                self.Ubtn = MDIconButton(
                    icon="arrow-up-bold-box-outline",
                    theme_text_color="Custom",
                    text_color=(1, 1, 1, 1),
                    md_bg_color="#6B7A8F",
                    pos_hint={"center_x": 0.5},
                    on_release=lambda *_: self.display_next(False), icon_size=50
                )
                self.add_widget(self.Ubtn)
            else:
                self.add_widget(Widget(height=15, size_hint_y=None))
            if header_text is not None:
                self.Header = HeaderLabel(text=header_text)
                self.add_widget(self.Header)
            self.add_widget(TLayout(self.L1, self.L2))

            if self.after:
                self.Dbtn = MDIconButton(icon="arrow-down-bold-box-outline", icon_size=50,
                                         theme_icon_color="Custom", md_bg_color="#6B7A8F", icon_color=(1, 1, 1, 1),
                                         pos_hint={"center_x": 0.5}, on_press=lambda *_: self.display_next(True))
                self.add_widget(self.Dbtn)
            else:
                self.add_widget(Widget(height=15, size_hint_y=None))
        else:
            self.L1 = CLabel(text=" ".join(text), pos_hint={"bottom": 0}, on_kv_post=self.update_pos if not update else Client.update_texts_pos)
            self.L2 = CLabel(text=" ".join(text2), pos_hint={"bottom": 0})
            if header_text is not None:
                self.Header = HeaderLabel(text=header_text)
                self.add_widget(self.Header)
            self.add_widget(TLayout(self.L1, self.L2))

    def update_pos(self, *_, preset_vals: list = None, client_call: bool = False) -> None:
        if client_call:
            preset_vals = self.last_pos_update
        if preset_vals is not None:
            if preset_vals[0]:
                self.L1.y = self.L2.y
            else:
                self.L2.y = self.L1.y
        if self.L1.y < self.L2.y:
            self.last_pos_update = [False, self.L1.texture_size[1] - self.L2.texture_size[1]]
            self.L2.y += self.last_pos_update[1]
        else:
            self.last_pos_update = [True, self.L2.texture_size[1] - self.L1.texture_size[1]]
            self.L1.y += self.last_pos_update[1]
        self.updating_next = False

    def process_text(self, text: list, text2: list) -> None:
        encountered = False
        tmp = []
        ctmp = [[], []]
        while len(text2) > len(text):
            text2[-2] = " ".join(text2[-2:])
            del text2[-1]
        while len(text2) < len(text):
            text[-2] = " ".join(text[-2:])
            del text[-1]
        for i, (t, t2) in enumerate(zip(text, text2)):
            if "[color=" in t:
                if not encountered:
                    encountered = True
                    ctmp[0].append(t)
                    ctmp[1].append(t2)
                else:
                    for c in tmp:
                        ctmp[0].append(c[0])
                        ctmp[1].append(c[1])
                    tmp.clear()
                    ctmp[0].append(t)
                    ctmp[1].append(t2)
            elif not encountered:
                self.before.append([t, t2])
            else:
                tmp.append([t, t2])
        if tmp:
            self.after.extend(tmp)
        if ctmp:
            ctmp[0] = " ".join(ctmp[0]).strip()
            ctmp[1] = " ".join(ctmp[1]).strip()
            self.current.extend(ctmp)

    def display_next(self, down: bool, *_) -> None:
        if not self.updating_next:
            self.updating_next = True
            if not Client.expanding:
                if down:
                    latin2, translation2 = self.after.pop(0)
                    self.L1.text = f"{self.current[0]} {latin2}"
                    self.L2.text = f"{self.current[1]} {translation2}"
                else:
                    latin, translation = self.before.pop(-1)
                    self.L1.text = f"{latin} {self.current[0]}"
                    self.L2.text = f"{translation} {self.current[1]}"
            else:
                if down:
                    latin2, translation2 = ("", "")
                    for t, t2 in self.after:
                        latin2 += f" {t}"
                        translation2 += f" {t2}"
                    self.L1.text = f"{self.current[0]} {latin2}"
                    self.L2.text = f"{self.current[1]} {translation2}"
                    self.after.clear()
                else:
                    latin, translation = ("", "")
                    for t, t2 in self.before:
                        latin += f" {t}"
                        translation += f" {t2}"
                    self.L1.text = f"{latin} {self.current[0]}"
                    self.L2.text = f"{translation} {self.current[1]}"
                    self.before.clear()
            if not self.after and self.Dbtn:
                self.remove_widget(self.Dbtn)
            if not self.before and self.Ubtn:
                self.remove_widget(self.Ubtn)
            self.current[0] = self.L1.text
            self.current[1] = self.L2.text
            Clock.schedule_once(lambda *_: Client.update_texts_pos(client_call=True))


class LateinApp(MDApp):
    def build(self) -> None:
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "BlueGray"
        self.theme_cls.theme_text_color = (1, 1, 1, 1)
        self.theme_cls.disable_shadow = True

    def on_start(self) -> None:
        self.current_widgets = []
        self.last_settings = []
        self.more_data = []
        self.load_more_btn = None
        self.last_search = ""
        self.ErrorLabel = None
        self.dialog = None
        self.add_more = False

        self.WaitingIcon = MDIconButton(icon="timer-sand", icon_size=250, disabled=True, disabled_color=(1, 1, 1, 1),
                                        pos_hint={"center_x": 0.5})
        self.waiting = False

        self.store = JsonStore("data.json")
        self.check_store()
        self.adjust_icons()

        self.Scraper = LateinScraper()
        self.DisplayWaiting()
        Thread(target=self.StartupLoading).start()

    def check_store(self) -> None:
        try:
            options = self.store.get("options")
            if options.get("marking") is not None:
                self.coloring = options.get("marking")
            else:
                self.coloring = True
            if options.get("expanding") is not None:
                self.expanding = options.get("expanding")
            else:
                self.expanding = False
            if options.get("always_expanding") is not None:
                self.always_expanding = options.get("always_expanding")
            else:
                self.always_expanding = False
            if options.get("display_title") is not None:
                self.display_title = options.get("display_title")
            else:
                self.display_title = True
            if options.get("max_display") is not None:
                self.max_display = options.get("max_display")
            else:
                self.max_display = 4
            self.store.put("options", marking=self.coloring, expanding=self.expanding, always_expanding=self.always_expanding, display_title=self.display_title, max_display=self.max_display)
        except KeyError:
            self.coloring = True
            self.expanding = False
            self.always_expanding = False
            self.display_title = True
            self.max_display = 4
            self.store.put("options", marking=True, expanding=False, always_expanding=False, display_title=True, max_display=4)
        finally:
            self.set_counter(str(self.max_display))
            self.last_settings = [self.coloring, self.expanding, self.always_expanding, self.display_title, self.max_display]

    def StartupLoading(self) -> None:
        if not self.Scraper.check_data(store=self.store):
            self.HandleConnectionError()
        else:
            self.RemoveWaiting()

    def adjust_icons(self) -> None:
        if self.expanding:
            self.toggle_chip("expanding")
        if not self.coloring:
            self.toggle_chip("markingc")
        if self.always_expanding:
            self.toggle_chip("always_expanding")
        if not self.display_title:
            self.toggle_chip("display_title")

    def on_stop(self) -> None:
        self.store.put("options", marking=self.coloring, expanding=self.expanding, always_expanding=self.always_expanding, display_title=self.display_title, max_display=self.max_display)

    def on_pause(self) -> bool:
        self.store.put("options", marking=self.coloring, expanding=self.expanding, always_expanding=self.always_expanding, display_title=self.display_title, max_display=self.max_display)
        return True

    @mainthread
    def HandleConnectionError(self) -> None:
        if self.waiting:
            self.RemoveWaiting()
        self.ErrorLabel = MDLabel(text="Keine Internetverbindung\nDrücken Sie auf 'Suchen' um es erneut zu versuchen",
                                  theme_text_color="Custom", text_color=(1, 0, 0, 1), halign="center",
                                  valign="center", font_style="H5")
        self.root.ids.cbox.add_widget(self.ErrorLabel)

    @mainthread
    def RemoveConnectionErrorLabel(self) -> None:
        try:
            self.root.ids.cbox.remove_widget(self.ErrorLabel)
        finally:
            self.ErrorLabel = None

    def TryConnectionAgain(self) -> None:
        if self.Scraper.check_data(store=self.store):
            self.RemoveConnectionErrorLabel()
            if self.waiting:
                self.RemoveWaiting()
        else:
            self.HandleConnectionError()

    @mainthread
    def DisplayWaiting(self, *_, animate: bool = True) -> None:
        self.root.ids.cbox.add_widget(self.WaitingIcon)
        self.waiting = True
        if animate:
            Clock.schedule_once(self.AnimateWaiting, 0.4)

    def AnimateWaiting(self, *_) -> None:
        self.WaitingIcon.icon = "timer-sand-complete" if self.WaitingIcon.icon == "timer-sand" else "timer-sand"
        if self.waiting:
            Clock.schedule_once(self.AnimateWaiting, 0.4)

    @mainthread
    def RemoveWaiting(self, *_) -> None:
        try:
            self.root.ids.cbox.remove_widget(self.WaitingIcon)
        finally:
            self.WaitingIcon.icon = "timer-sand"

    @mainthread
    def add_translation(self, text: list, text2: list, header_text: str = None, update: bool = False, always_expanding: bool = None) -> None:
        if always_expanding is None:
            always_expanding = self.always_expanding
        self.current_widgets.append(TranslationLayout(text, text2, always_expanding, header_text=header_text, update=update))
        self.current_widgets.append(MDSeparator())
        self.root.ids.cbox.add_widget(self.current_widgets[-2])
        self.root.ids.cbox.add_widget(self.current_widgets[-1])

    @mainthread
    def add_nothing_found(self) -> None:
        self.current_widgets.append(CLabel(text="Es wurde nichts gefunden" if all(self.Scraper.data) else
            "Es wurde nichts gefunden\nScheinbar sind auch keine Daten vorhanden\nBitte aktualisieren sie die Daten", halign="center", valign="center", font_style="H4"))
        self.current_widgets.append(MDSeparator())
        self.root.ids.cbox.add_widget(self.current_widgets[-2])
        self.root.ids.cbox.add_widget(self.current_widgets[-1])

    @mainthread
    def clear(self, *_) -> None:
        self.current_widgets.clear()
        self.root.ids.cbox.clear_widgets()

    def search(self, *_) -> None:
        if self.ErrorLabel is None:
            if self.root.ids.search_field.text.strip() and self.settings_different():
                self.root.ids.search_btn.disabled = True
                self.last_search = self.root.ids.search_field.text.strip()
                if self.add_more:
                    self.Remove_load_more_btn()
                self.clear()
                data = self.Scraper.get_from_substr(self.last_search, title_return=True)
                titles = data[0]
                if titles:
                    if len(titles) > self.max_display:
                        self.more_data = [titles[self.max_display:], data[1][self.max_display:]]
                        titles = titles[:self.max_display]
                        self.add_more = True
                    else:
                        self.add_more = False
                        self.more_data = []
                    for i, title in enumerate(titles):
                        latin = data[1][i][0]
                        translated = data[1][i][1]
                        for j, chunk in enumerate(latin):
                            if (" " + self.last_search.lower()) in (" " + chunk.lower()) or self.last_search.lower() in chunk.lower():
                                if self.coloring:
                                    latin[j] = f"[color=#9999cc]{chunk}[/color]"
                                    if len(translated) == len(latin):
                                        translated[j] = f"[color=#9999cc]{translated[j]}[/color]"
                                else:
                                    latin[j] = f"[color=#FFFFFF]{chunk}[/color]"
                                    if len(translated) == len(latin):
                                        translated[j] = f"[color=#FFFFFF]{translated[j]}[/color]"
                        self.last_settings = [self.coloring, self.expanding, self.always_expanding, self.display_title, self.max_display]
                        self.add_translation(latin, translated, header_text=title if self.display_title else None)
                    if self.add_more:
                        self.add_load_more_btn()
                else:
                    self.add_nothing_found()
                self.root.ids.search_btn.disabled = False
                Clock.schedule_once(self.RemoveWaiting)
        else:
            self.RemoveConnectionErrorLabel()
            self.DisplayWaiting()
            Thread(target=self.TryConnectionAgain).start()

    @mainthread
    def load_more(self, *_) -> None:
        self.Remove_load_more_btn()
        if self.more_data[0] and self.more_data[1]:
            if len(self.more_data[0]) > self.max_display:
                titles = self.more_data[0][:self.max_display]
                data = self.more_data[1][:self.max_display]
                del self.more_data[0][:self.max_display]
                del self.more_data[1][:self.max_display]
                self.add_more = True
            else:
                titles = self.more_data[0]
                data = self.more_data[1]
                self.add_more = False
                self.more_data = []
            for i, title in enumerate(titles):
                latin = data[i][0]
                translated = data[i][1]
                for j, chunk in enumerate(latin):
                    if (" " + self.last_search.lower()) in (
                            " " + chunk.lower()) or self.last_search.lower() in chunk.lower():
                        if self.coloring:
                            latin[j] = f"[color=#9999cc]{chunk}[/color]"
                            if len(translated) == len(latin):
                                translated[j] = f"[color=#9999cc]{translated[j]}[/color]"
                        else:
                            latin[j] = f"[color=#FFFFFF]{chunk}[/color]"
                            if len(translated) == len(latin):
                                translated[j] = f"[color=#FFFFFF]{translated[j]}[/color]"
                self.add_translation(latin, translated, header_text=title if self.display_title else None, update=i == len(titles)-1)
            if self.add_more:
                self.add_load_more_btn()
        Clock.schedule_once(lambda *_: self.update_texts_pos(client_call=True))

    @mainthread
    def Remove_load_more_btn(self) -> None:
        self.root.ids.cbox.remove_widget(self.load_more_btn)
        self.add_more = False

    @mainthread
    def add_load_more_btn(self, *_) -> None:
        if self.load_more_btn is None:
            self.load_more_btn = MDRectangleFlatIconButton(text="Mehr anzeigen", icon="expand-all",
                                          icon_size=60, md_bg_color=(0.2, 0.2, 0.2, 1), line_color=(0.4, 0.6, 0.8, 1),
                                          theme_text_color="Custom", ripple_color=(0, 0.5, 0.5, 0.5), radius=[15],
                                          pos_hint={"center_x": 0.5, "center_y": 0.5}, icon_color="white",
                                          on_press=lambda *_: Clock.schedule_once(self.load_more), text_color="white")
        self.root.ids.cbox.add_widget(self.load_more_btn)

    @mainthread
    def update_texts_pos(self, *_, exclude: Widget = None, client_call: bool = False) -> None:
        for w in self.current_widgets:
            if isinstance(w, TranslationLayout) and w is not exclude:
                w.update_pos(client_call=client_call)

    def validate_search_field(self, instance, *_) -> None:
        if instance.text:
            if self.root.ids.search_field.text.strip() and self.settings_different() and self.ErrorLabel is None:
                Clock.schedule_once(self.clear, -1)
                Clock.schedule_once(self.DisplayWaiting, -1)
            Clock.schedule_once(lambda *_: Thread(target=self.search).start(), 0.05)

    def settings_different(self, *_) -> bool:
        return bool(self.root.ids.search_field.text.strip() != self.last_search or self.last_settings[0] !=
                    self.coloring or self.display_title != self.last_settings[3] or self.expanding !=
                    self.last_settings[1] or self.always_expanding != self.last_settings[2] or self.last_settings[4] != self.max_display)

    @staticmethod
    def back_click(__, key, *_) -> bool:
        if key == 27:
            return True

    def toggle_chip(self, name: str) -> None:
        if getattr(self.root.ids, name).selected:
            getattr(self.root.ids, name).selected = False
            if name == "markingc":
                self.coloring = False
            elif name == "expanding":
                self.expanding = False
            elif name == "always_expanding":
                self.always_expanding = False
            elif name == "display_title":
                self.display_title = False
            getattr(self.root.ids, name).icon_left = "circle-off-outline"
            getattr(self.root.ids, name).icon_left_color = (1, 0, 0, 1)
        else:
            getattr(self.root.ids, name).icon_left = "check-circle-outline"
            getattr(self.root.ids, name).selected = True
            if name == "markingc":
                self.coloring = True
            elif name == "expanding":
                self.expanding = True
            elif name == "always_expanding":
                self.always_expanding = True
            elif name == "display_title":
                self.display_title = True
            getattr(self.root.ids, name).icon_left_color = (0, 1, 0, 1)

    def increase_counter(self) -> None:
        nval = int(self.root.ids.counter.ids.current_count.text) + 1
        if nval > 0:
            self.root.ids.counter.ids.current_count.text = str(nval)
            self.max_display = nval

    def decrease_counter(self) -> None:
        nval = int(self.root.ids.counter.ids.current_count.text)-1
        if nval > 0:
            self.root.ids.counter.ids.current_count.text = str(nval)
            self.max_display = nval

    @mainthread
    def set_counter(self, value: str) -> None:
        self.root.ids.counter.ids.current_count.text = value

    def delete_data(self) -> None:
        self.root.ids.data_del_btn.disabled = True
        if self.dialog is None:
            self.dialog = MDDialog(
                text="Daten wirklich löschen?",
                buttons=[MDFlatButton(text="Abbrechen", theme_text_color="Custom",
                                      text_color=self.theme_cls.primary_color,
                                      on_release=self.dialog_dismiss),
                         MDFlatButton(text="Löschen", theme_text_color="Custom",
                                      text_color=(0.686, 0.133, 0.133, 1),
                                      on_release=self.dialog_delete)])
        self.dialog.open()

    def dialog_dismiss(self, *_) -> None:
        self.dialog.dismiss()
        Clock.schedule_once(lambda *_: self.enable_btn("data_del_btn"), 0.35)

    def enable_btn(self, btn_id: str) -> None:
        getattr(self.root.ids, btn_id).disabled = False

    def dialog_delete(self, *_) -> None:
        self.dialog.dismiss()
        self.store.delete("data")
        self.Scraper.data = [[], []]
        self.last_search = ""
        self.clear()
        Clock.schedule_once(lambda *_: self.enable_btn("data_del_btn"), 0.35)

    def change_reload_btn_icon(self, icon: str, icon_color: tuple = None) -> None:
        self.root.ids.data_re_btn.icon = icon
        if icon_color is not None:
            self.root.ids.data_re_btn.icon_color = icon_color

    def reload_data(self) -> None:
        self.root.ids.data_re_btn.disabled = True
        Clock.schedule_once(lambda *_: self.change_reload_btn_icon("timer-sand", (1, 1, 1, 1)), -1)
        Thread(target=self.finish_reloading).start()

    def finish_reloading(self, *_) -> None:
        if not self.Scraper.check_data(store=self.store, load_from_store=False):
            self.change_reload_btn_icon("wifi-cancel", (1, 0, 0, 1))
        else:
            self.change_reload_btn_icon("reload", (0, 1, 0, 1))
            self.last_search = ""
        Clock.schedule_once(lambda *_: self.enable_btn("data_re_btn"), 0.35)


Client = LateinApp()
Client.run()
