import spacy
from spacy.matcher import PhraseMatcher
from typing import List


class DeviceDetector:
    """Detect devices in user command using fuzzy keyword matching."""

    def __init__(self):
        # Keywords for washing machine
        self.washing_keywords: List[str] = [
            "washing machine", "washingmachine", "washer", "laundry machine",
            "laundry", "spin cycle", "rinse cycle", "wash cycle",
            "wash clothes", "wash clothing", "start laundry", "launder",
            "laundering", "washin machine", "washng machine", "washinmachin",
            "washin machne", "wash machne", "washerr", "washer machine",
            "washer machinee", "washr", "laundy", "laundr", "laundrie machine",
            "wash clothes please", "plz wash clothes", "start wash",
            "begin washing", "washinh machne", "washhing machne",
            "wasing machine", "washing machne", "washing macine",
            "wshing machine", "washing mchine", "washin mchine",
            "washig machine", "do laundry", "laundry load", "load of laundry",
            "clothes wash", "wash my clothes", "clean clothes", "fold clothes",
            "start wash cycle", "start rinse cycle", "start spin cycle",
            "turn on washing machine", "turn on washer",
            "activate washing machine", "activate washer", "please do laundry",
            "laundry please", "could you wash clothes",
            "please wash my laundry", "wash my garments", "clean my clothes",
            "launder clothes", "launder my clothes"
        ]
        # Keywords for dishwasher
        self.dishwasher_keywords: List[str] = [  # synonyms for dishwasher
            "dishwasher", "dish washer", "dishwashing", "dishes",
            "wash dishes", "clean dishes", "start dishwasher",
            "run dishwasher", "dish cycle", "rinse dishes",
            "wash cycle dishes", "dishwaher", "dishwaser", "dishwashe",
            "dish washr", "dishwaser machine", "dish washerr",
            "dishwash machine", "clean dshes", "cleen dishes",
            "clr dishes", "pls wash dishes", "plz clean dishes",
            "start dishwash", "run dishwashing", "dishwshr",
            "dishahsher", "dishshasher", "dishwahserr",
            "dishwashr", "dish wshing", "dish wahser",
            "dish washr", "dshwasher", "dishwshing",
            "start dish cycle", "start rinse cycle dishes",
            "turn on dishwasher", "activate dishwasher",
            "please wash dishes", "could you wash dishes",
            "load dishwasher", "empty dishwasher",
            "run the dishes please", "wash the dishes please",
            "clean the dishes", "could you clean dishes",
            "dishwasher please"
        ]
        # Initialize spaCy model
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            self.nlp = spacy.blank("en")
        # Create PhraseMatcher for multi-word patterns
        self.matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        self._init_matcher()

    def _init_matcher(self):
        patterns_wash = [
            self.nlp.make_doc(text)
            for text in self.washing_keywords
        ]
        patterns_dish = [
            self.nlp.make_doc(text)
            for text in self.dishwasher_keywords
        ]
        self.matcher.add("WASHING_MACHINE", patterns_wash)
        self.matcher.add("DISHWASHER", patterns_dish)

    def detect(self, text: str) -> List[str]:
        """Return a list of devices matched in the input text."""
        doc = self.nlp(text.lower())
        found = set()
        for match_id, start, end in self.matcher(doc):
            label = self.nlp.vocab.strings[match_id]
            if label == "WASHING_MACHINE":
                found.add("washing_machine")
            elif label == "DISHWASHER":
                found.add("dishwasher")
        return list(found)
