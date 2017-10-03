from bs4 import BeautifulSoup
import urllib2
import pandas as pd
from itertools import combinations
import numpy as np
from joblib import Parallel, delayed
import datetime

base_page = ['http://games.espn.com/fhl/playerrater?slotCategoryGroup=1&', \
	'http://games.espn.com/fhl/playerrater?slotCategoryGroup=2&']
addon = '&startIndex='
startindex = list(range(50, 750, 50))
plyr_dict = {}
for page in base_page:
	original_page = page
	for i in startindex:
		get_page = urllib2.urlopen(page)
		soup = BeautifulSoup(get_page, 'html.parser')
		rows = soup.find_all('tr')
		for row in rows:
			if len(row) == 15:
			    if row.a.get_text()!='PLAYER':
				try:
					plyr_dict[row.a.get_text()] = [float(td.string) \
					for td in row.find_all('td', {'class': \
					'playertableData sortedCell'})][0]
				except:
					continue
		page = original_page + addon + str(i)

df = pd.read_csv('fanduel_9.csv').set_index('Nickname')
df['Projection'] = pd.DataFrame.from_dict(plyr_dict, orient='index')
df = df.reset_index()
df = df.reset_index().set_index('Nickname')
df = df[df['Injury Indicator'].isnull()]
df[df['Projection'].isnull()]
df = df[df['Projection'] > 1]

min_salary = df.groupby(['Position'])['Salary'].agg([np.min])['amin'].to_dict()
min_c_projection = df[df['Salary'] == min_salary['C']][df['Position'] == 'C']['Projection'].max()
min_w_projection = df[df['Salary'] == min_salary['W']][df['Position'] == 'W']['Projection'].max()
min_d_projection = df[df['Salary'] == min_salary['D']][df['Position'] == 'D']['Projection'].max()
min_g_projection = df[df['Salary'] == min_salary['G']][df['Position'] == 'G']['Projection'].max()
min_dict = {'C': min_c_projection, 'W': min_w_projection,\
         'D': min_d_projection, 'G': min_g_projection}


grouped = df.groupby(['Position'])
position_dict = {}
for pos, frame in grouped:
    position_dict[pos] = frame[frame['Projection'] > min_dict[pos]].to_dict(orient='index')
player_dict = {}
for item in position_dict.items():
        for plyr_name in item[1].keys():
                player_dict[plyr_name] = item[1][plyr_name]


def total_lineup(g, c, w, d, key):
	team_list = []
	c = [x for x in c]
	w = [x for x in w]
	d = [x for x in d]
	team_list = [g] + c + w + d
	return round(sum([player_dict[x][key] for x in team_list]), 2)

 
def run(single_position):
	optimal_lineup_projection = 0
	optimal_lineup = []
	g = single_position
	for c in combinations(position_dict['C'], 2):
		for w in combinations(position_dict['W'], 4):
			for d in combinations(position_dict['D'], 2):
				salary = total_lineup(g, c, w, d, 'Salary')	
				if 59500 < salary <= 60000:
					lineup = total_lineup(g, c, w, d, 'Projection')
					if lineup >= optimal_lineup_projection:
						optimal_lineup_projection = lineup
						optimal_lineup = [g, c, w, d]
	print (optimal_lineup_projection, optimal_lineup)
	return (optimal_lineup_projection, optimal_lineup)


def get_combo_list():
	return [(g) for g in position_dict['G'].keys()] 


if __name__=="__main__":
	start_time = datetime.datetime.now()
	results = Parallel(n_jobs=-1)(delayed(run)(i) for i in get_combo_list())
	print (len(results))
	max_projection = 0
	team = []
	for i in results:
		if i[0] > max_projection:
			max_projection = i[0]
			team = i[1]

	print (datetime.datetime.now() - start_time)
	print (max_projection, team)
	df = pd.DataFrame(results)
	df.to_csv('results.csv)
