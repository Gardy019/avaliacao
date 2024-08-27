import pandas as pd
import os
from datetime import timedelta

# Pastas de input e output
FOLDER_INPUT = r"./data/input"
FOLDER_OUTPUT = r"./data/output"

# Arquivos com os caminhos ajustados
DISTANCIAS = os.path.join(FOLDER_INPUT, r"distances.csv")
CUSTOS = os.path.join(FOLDER_INPUT, r"freight_costs.csv")
NOME_ARQUIVO_OUTPUT_1 = os.path.join(FOLDER_OUTPUT, r"output_1.csv")
NOME_ARQUIVO_OUTPUT_2 = os.path.join(FOLDER_OUTPUT, r"output_2.csv")

DESTINOS = [1501303, 1506807, 3205309, 3548500, 4118204, 4207304, 4216206, 4315602]

#função usada para converter o tipo dos dados das colunas
def converter_formato(df, **colunas):

    for coluna, tipo in colunas.items():
        if tipo == 'int':
            df[coluna] = df[coluna].str.replace(',', '.', regex=False)
            df[coluna] = pd.to_numeric(df[coluna], errors='coerce').astype('Int64')
        elif tipo == 'float':
            if df[coluna].dtype == 'object':
                df[coluna] = df[coluna].str.replace(',', '.', regex=False)
                df[coluna] = df[coluna].str.strip()
            df[coluna] = pd.to_numeric(df[coluna], errors='coerce')
        elif tipo == 'datetime':
            df[coluna] = pd.to_datetime(df[coluna], errors='coerce', dayfirst=True)
        else:
            raise ValueError(f"Tipo de conversão '{tipo}' não é suportado para a coluna '{coluna}'.")
    return df

# Le os arquivos e converte as colunas necessarias
distancias_data = pd.read_csv(DISTANCIAS, delimiter=';')
converter_formato(distancias_data, distance='float')

frete_data = pd.read_csv(CUSTOS, delimiter=';')
converter_formato(frete_data, id_city_origin='int',
                            id_city_destination='int',
                            freight_cost='float',
                            dt_reference='datetime')

# Filtra os destinos
frete_data_filtrado = frete_data[frete_data['id_city_destination'].isin(DESTINOS)]
output_1 = pd.merge(frete_data_filtrado, distancias_data, on=['id_city_origin', 'id_city_destination'], how='left')

# Salvando o resultado final em CSV do output 1
output_1.to_csv(NOME_ARQUIVO_OUTPUT_1, sep=';', index=False)


# por conta dos modelos de machine leraning (regressão linear e random forest) não terem me ajudado a trazer um dado "correto" eu resolvi fazer por média
output_1['dt_reference'] = pd.to_datetime(output_1['dt_reference'], dayfirst=True)
output_1['week_of_year'] = output_1['dt_reference'].dt.isocalendar().week
output_1['year'] = output_1['dt_reference'].dt.year

# Cria um DataFrame para armazenar as próximas 52 semanas
output_2 = pd.DataFrame()

# Definindo a data de referência inicial (primeira semana depois da maior data que aparecia)
data_inicial_teste = output_1['dt_reference'].max() + timedelta(days=7)

# Processar cada grupo de distância que uso para separar as rotas
for distancia in output_1['distance'].unique():
    subset = output_1[output_1['distance'] == distancia]
    
    # calculando a média semanal para cada grupo de distância
    media_semanal_frete = subset.groupby(['week_of_year'])['freight_cost'].mean().reset_index()
    
    # Repetir a lista de médias até atingir 52 semanas
    media_repitida_frete = media_semanal_frete['freight_cost'].tolist() * (52 // len(media_semanal_frete) + 1)
    media_repitida_frete = media_repitida_frete[:52]  # Garante que temos exatamente 52 semanas
    
    # Gerar as próximas 52 semanas
    proximas_semanas = pd.DataFrame({
        'dt_reference': [data_inicial_teste + timedelta(weeks=i) for i in range(52)],
        'id_city_origin': subset['id_city_origin'].iloc[0],
        'id_city_destination': subset['id_city_destination'].iloc[0],
        'freight_cost': media_repitida_frete,
        'distance': subset['distance'].iloc[0]
    })
    
    # Adicionar ao dataFrame final
    output_2 = pd.concat([output_2, proximas_semanas])

# Reformatando a data para o formato 'dd/mm/yyyy e tambem arredondo por conta de problemas anteriores'
output_2['dt_reference'] = output_2['dt_reference'].dt.strftime('%d/%m/%Y')
output_2['freight_cost'] = output_2['freight_cost'].round(2)

# Salvando o resultado final em CSV
output_2.to_csv(NOME_ARQUIVO_OUTPUT_2, sep=';', index=False)