from city_road_network.downloaders.stats import get_nhts_dataset, get_russtat_data

if __name__ == "__main__":
    df_trips = get_nhts_dataset("trippub.csv")  # or other dataset name
    df = get_russtat_data()

    # do your research...
