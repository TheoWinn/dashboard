from bertopic import BERTopic
from bertopic.representation import MaximalMarginalRelevance
from sklearn.datasets import fetch_20newsgroups


#Just some example data from sklearn.
corpus = fetch_20newsgroups(subset='all',  remove=('headers', 'footers', 'quotes'))['data']


#topic_model = BERTopic()



#Maybe we want to use Maximal Marginal Relevance for topic representation

representation_model = MaximalMarginalRelevance(diversity=0.3)

topic_model = BERTopic(representation_model=representation_model)

topics, probs = topic_model.fit_transform(corpus)

# Use hierarchical structure on already fitted model
#Problem: Which linkage function do we want to use? Default: ward function ->sensitive to outliers2 merges topic with smallest increase in variance
#Other options: complete, average, single, etc.
#hierarchical_topics = topic_model.hierarchical_topics(corpus)

#Calculate topics and probabilities of topics


print("Hello world")