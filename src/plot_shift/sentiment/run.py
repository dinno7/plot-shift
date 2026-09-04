from plot_shift.sentiment import VaderLexiconScorer, VADLexiconScorer

if __name__ == "__main__":
    # Dictionary organized by sentiment category
    test_sentences = {
        "positive": [
            "I absolutely love this product! It's amazing and exceeded all my expectations.",
            "What a wonderful day! The weather is beautiful and I'm feeling great.",
            "This restaurant serves the best food I've ever had. Highly recommended!",
            "I'm so grateful for your help. You made my life so much easier.",
            "This movie was fantastic. The acting, plot, and cinematography were all excellent.",
        ],
        "negative": [
            "This is the worst experience I've ever had. Completely disappointed.",
            "I hate waiting in long lines. It's frustrating and wastes my time.",
            "The quality of this item is terrible. It broke after one day.",
            "I'm so angry about how I was treated. Unacceptable behavior.",
            "This book was boring and predictable. A complete waste of time.",
        ],
        "neutral": [
            "The meeting is scheduled for tomorrow at 3 PM.",
            "The temperature outside is 22 degrees Celsius.",
            "She lives in New York and works as an engineer.",
            "This car is blue and has four doors.",
            "The report contains data from the past year.",
        ],
        "mixed": [
            "The food was excellent, but the service was incredibly slow.",
            "I like the design, although it's a bit expensive for my budget.",
            "The movie had some great moments, but overall it was disappointing.",
            "The product quality is good, but customer support is lacking.",
            "I'm excited about the new job, but nervous about moving to a new city.",
        ],
    }

    vader_model = VaderLexiconScorer()
    vad_model = VADLexiconScorer("/home/dinno/codes/plot-shift/data/raw/lexicons/vad_lexicon.txt")
    print("\n\nTest data format (sentence, label):")
    print("------------------------------")
    for label, sentences in test_sentences.items():
        for sentence in sentences:
            print(f"{label:10}:", sentence)

            vader_score = vader_model.score(sentence)
            print(f"{'Vader':10}:", vader_score)

            vad_score = vad_model.score(sentence)
            print(f"{'VAD':10}:", vad_score)

            print("---------------")
