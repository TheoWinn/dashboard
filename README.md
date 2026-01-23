# Mismatch Barometer Dashboard

This dashboard compares which issues are discussed in the German Bundestag with those debated in the public sphere, specifically in German talk shows.The final product is a dashboard that is able to quantify which topics exist in both spheres, how much time each topic receives per sphere (in minutes), and which sphere contributes how much to the overall time talked about. in the Bundestag and the talk shows.The dashboard thus illustrates communication gaps and differences in issue salience.

The final product is a dashboard that is able to quantify which topics exist in both spheres, how much time each topic receives per sphere (in minutes), and which sphere contributes how much to the overall time talked about.

## How To Access The Dashboard

You can view the dashboard directly and conveniently [here](https://theowinn.github.io/dashboard/).

## How It Works

### Data Generation Process

The project utilizes multiple data sources.

First of all, we call the German Bundestag API to gain access to the official stenographic transcripts of Bundestag plenary meetings. This unlocks access to who says what, and what party affiliations each speaker has.

We also download official plenary meeting recordings from the Bundestag. These are then transcribed using WhisperX, and allow us to estima te the time that a single speaker allocates to a specific topic. These automated, and subsequently also timestamped, transcripts are matched to their official counterparts of the Bundestag API, so we have the official transcript of who says what, in addition to how long they speak.

We also download a set of German talk shows and transcribe them in a similar manner to the Bundestag recordings. This enables us to gain access to timestamped transcripts of various talk shows.

### Data Analyzation

We pass the data from the matched Bundestag transcripts and the transcripts of the talk shows to a BERTopic model. This model discovers the topics that are present across both spheres. Topics live in the same embedding space which enables comparability.

Employing the BERTopic model allows us to genereate coherent topic clusters, that are associated with a unique topic ID, words representing each topic as well as an exemplary text exzerpt that demonstrates which kind of text passage would be assigned to each topic.

As these labels are numeric and don't bear substantive meaning, we pass the representative words to an LLM that generates human-interpretable topic labels. 

### Metric Computation & Data Storage

After the BERTopic model has clustered the embedded text sequences and labels have been generated, we are able to compute how much time each topic was talked about per sphere and can derive numerous ways to quantify the amount of time allocated per topic. 

- `topic_duration` quantifies how much time a single topic was talked about across both spheres (format: hh:mm:ss.sss)
- `topic_duration_bt` & `topic_duration_bt` quantify how much time each topic has been talked about per sphere
- `bt_normalized_perc` & `ts_normalized_perc` quantify the normalized speechtime per sphere, and is constructed as follows: $\frac{\text{topic speechtime Bundestag} \mid \text{Talk shows}}{\text{overall speech time in Bundestag} \mid \text{Talk shows}}$
- `bt_share` & `ts_share` depict the normalized share of the topic salience in each sphere, and is computed as follows: $\frac{\text{bt-normalized-perc} \mid \text{ts-normalized-perc}}{\text{bt-normalized-perc + ts-normalized-perc}}$
- `mismatch_ppoints` is the difference between the normalized sphere percenages ranging from $-100$ to $100$; values $> 0$ indicate more salience in the Bundestag, a value $<0$ show more salience in the Talk shows, and a value of $0$ signifies equal salience
- `mismatch_log_ratio` is the log ration of the normalized speech times, and is constructed as follows: 
$\log\!\left(\frac{\text{bt-normalized-perc} + 0.0000001}{\text{ts-normalized-perc} + 0.0000001}\right)$; positive values indicate more salience in the Bundestag, negative ones more salience in the Talk shows, $0$ indicates an equilibrium.

These values are computed using the database in which we store all of our generated data. For more details, please view the `database` folder.

## Use For Your Own Project

Should you wish to apply this kind of structure to your own project, analyzing two different spheres to the ones in this project, you can clone this project's repository using `git clone https://github.com/TheoWinn/dashboard`.

If you want to use the exact process, you may also need to enter your own environment variables, especially: 
- API keys that you may need for accessing the data of your choice 

- a Hugging Face Token

- API key to the LLM of your choice

- URL of your database 

- Access key to your database