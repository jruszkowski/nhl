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

df = pd.read_csv('draftkings.csv').set_index('Name')
df['Projection'] = pd.DataFrame.from_dict(plyr_dict, orient='index')
df = df.reset_index()
df['Name'] = df['Name'].apply(lambda x: x.strip())
df.set_index(['Name'], inplace=True)
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


def total_lineup_all(combo, key):
        g = combo[0]
        c = combo[1]
        w = combo[2]
        d = combo[3]

	c = [x for x in c]
	w = [x for x in w]
	d = [x for x in d]
	team_list = [g] + c + w + d
	return round(sum([player_dict[x][key] for x in team_list]), 2)


def create_salary_dict():
        return {salary: {'players': [], 'projection': 0, 'count': 0} for salary in range(0,55100,100)}

combos = {'C': 3, 'C': 2, 'W': 3, 'W': 4, 'D': 3, 'D': 2}
combo_dict = {1: {'C': 3, 'W': 3, 'D': 2}, 
	  2: {'C': 2, 'W': 4, 'D': 2}, 
	  3: {'C': 2, 'W': 3, 'D': 3}}

c_dict = create_salary_dict()
w_dict = create_salary_dict()
d_dict = create_salary_dict()
g_list = [g for g in position_dict['G'].keys()]

def create_combo_dictionaries(combo_args):
        position = combo_args[0]
        count = combo_args[1]
        if position == 'C':
                for combo in combinations(position_dict[position], count):
                        projection = add_func(position, combo, 'Projection')
                        salary = add_func(position, combo, 'Salary')
                        if projection > c_dict[salary]['projection']:
                                c_dict[salary]['projection'] = projection
                                c_dict[salary]['players'] = combo
                                c_dict[salary]['count'] = count
        elif position == 'W':
                for combo in combinations(position_dict[position], count):
                        projection = add_func(position, combo, 'Projection')
                        salary = add_func(position, combo, 'Salary')
                        if projection > w_dict[salary]['projection']:
                                w_dict[salary]['projection'] = projection
                                w_dict[salary]['players'] = combo
                                w_dict[salary]['count'] = count
        elif position == 'D':
                for combo in combinations(position_dict[position], count):
                        projection = add_func(position, combo, 'Projection')
                        salary = add_func(position, combo, 'Salary')
                        if projection > d_dict[salary]['projection']:
                                d_dict[salary]['projection'] = projection
                                d_dict[salary]['players'] = combo
                                d_dict[salary]['count'] = count


def clean_dict(dict_zeros):
        for key in dict_zeros.keys():
                if dict_zeros[key]['projection'] == 0:
                        del dict_zeros[key]
        return dict_zeros

def add_func(position, plyrs, key):
        plyrs = [x for x in plyrs]
        return sum([position_dict[position][x][key] for x in plyrs])

if __name__=="__main__":
	start_time = datetime.datetime.now()
        Parallel(n_jobs=-1)(delayed(create_combo_dictionaries)(i) for i in combos.items())
	c_dict = clean_dict(c_dict)
	w_dict = clean_dict(w_dict)
	d_dict = clean_dict(d_dict)

	for key in combo_dict.keys():
		total_dict = {(g, c_dict[c]['players'], w_dict[w]['players'], d_dict[d]['players']): \
			{'salary': total_lineup_all((g, \
					c_dict[c]['players'], \
					w_dict[w]['players'], \
					d_dict[d]['players']), 'Salary'),\
			 'projection': total_lineup_all((g, \
					c_dict[c]['players'], \
					w_dict[w]['players'], \
					d_dict[d]['players']), 'Projection')} \
			for g in g_list \
			for c in c_dict.keys() \
			for w in w_dict.keys() \
			for d in d_dict.keys() \
			if total_lineup_all((g, \
				c_dict[c]['players'], w_dict[w]['players'], d_dict[d]['players']), 'Salary') <= 55000 \
				and c_dict[c]['count'] == combo_dict[key]['C'] \
				and w_dict[c]['count'] == combo_dict[key]['W'] \
				and d_dict[c]['count'] == combo_dict[key]['D'] }



	max_projection = max([total_dict[x]['projection'] for x in total_dict.keys()])
        for key in total_dict.keys():
                if total_dict[key]['projection'] == max_projection:
                        print key
        print (datetime.datetime.now() - start_time)
