# model/lexicon.py

REBEL = {
    "keywords": [
        "break","break rules","rule breaking","rule-breaking","rebel","outlaw","defy","defiant",
        "disrupt","nonconformist","unapologetic","maverick","against the grain","anarchy","riot",
        "unbound","bold","independent","freedom","smash","refuse","resist","revolt"
    ],
    "replace": {"innovative":"rule-breaking","features":"firepower","solutions":"weapons","technology":"anarchy-grade tech"},
    "templates": [
        "We {verb} the rules so you can {benefit}.",
        "No permission needed. {brand} {verb2} limits.",
        "{brand} is for the ones who {verb3} conformity."
    ],
    "verbs": ["break","defy","smash"],
    "verbs2": ["obliterates","wrecks"],
    "verbs3": ["refuse","destroy"],
    "benefits": ["move free","own your path"],
}

CAREGIVER = {
    "keywords": [
        "care","caring","nurture","nurturing","protect","protection","support","supportive",
        "safe","safety","compassion","compassionate","empathy","gentle","warm","warmth",
        "embrace","family","trust","wellbeing","well being","well-being","shield","comfort",
        "soothe","reassure","healing","kindness","help","tender","listen"
    ],
    "replace": {"features":"care standards","technology":"care tech"},
    "templates": [
        "{brand} is here to {verb} you—every step.",
        "Because your {benefit} deserves gentle, proven care."
    ],
    "verbs": ["support","protect"],
    "benefits": ["family","peace of mind"],
}

EXPLORER = {
    "keywords": [
        "explore","discover","adventure","freedom","wander","roam","journey","trail","frontier",
        "off road","off-road","beyond","horizon","wild","map","path","route","expedition",
        "uncharted","out there","find your own way"
    ],
    "replace": {"features":"trail tools","technology":"navigation tech"},
    "templates": [
        "Go {verb} the map—{brand} equips your {benefit}.",
        "Every path is a story. {brand} gets you there."
    ],
    "verbs": ["beyond","off"],
    "benefits": ["next route","bold journey"],
}

ARCHETYPES = {"Rebel": REBEL, "Caregiver": CAREGIVER, "Explorer": EXPLORER}