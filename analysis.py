import numpy as np
import pandas as pd


def haversine(lon1, lat1, lon2, lat2):
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    # Haversine formula
    longitude_distance = lon2 - lon1
    latitude_distance = lat2 - lat1
    a = (
        np.sin(latitude_distance / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin(longitude_distance / 2) ** 2
    )
    c = 2 * np.arcsin(np.sqrt(a))

    # Radius of earth in meters (use 3956 for miles)
    r = 6371000

    return c * r


def drop_same_events(df, min_distance=40):
    events_to_drop = set()

    for i in range(len(df)):
        for j in range(i + 1, len(df)):

            # Calculate distance if two events have the same title
            if df.iloc[i]["Category"] == df.iloc[j]["Category"]:
                dist = haversine(
                    df.iloc[i]["Start Longitude"],
                    df.iloc[i]["Start Latitude"],
                    df.iloc[j]["Start Longitude"],
                    df.iloc[j]["Start Latitude"],
                )
                dist_feet = dist * 3.28
                if dist_feet <= min_distance:
                    events_to_drop.add(df.iloc[j]["Event ID"])

    print(f"Dropping {len(events_to_drop)} events.", events_to_drop)
    df = df[~df["Event ID"].isin(events_to_drop)]
    return df


def get_distance(event_id1, event_id2, df):
    # Find the rows corresponding to the event IDs
    row1 = df[df["Event ID"] == event_id1]
    row2 = df[df["Event ID"] == event_id2]

    # Check if both events exist in the DataFrame
    if row1.empty or row2.empty:
        return "One or both Event IDs not found in the DataFrame."

    # Extracting coordinates
    lon1, lat1 = row1.iloc[0]["Start Longitude"], row1.iloc[0]["Start Latitude"]
    lon2, lat2 = row2.iloc[0]["Start Longitude"], row2.iloc[0]["Start Latitude"]

    # Calculate and return the distance
    return haversine(lon1, lat1, lon2, lat2)


if __name__ == "__main__":
    file_name = "traffic_events.csv"
    df = pd.read_csv(file_name)
    print(get_distance(1701650, 1701609, df))
    # df["Start Time"] = pd.to_datetime(df["Start Time"])
    # df = drop_same_events(df)
    # df.to_csv(file_name, index=False)
