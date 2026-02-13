# DATA 551 - Dashboard Proposal
**Project title:** Spotify Track Insights Explorer  
**Group 7 Members:** Jingtao Yang, Zihao Sheng, Richard Hua, Yihang Wang


## 1. Motivation and Purpose

Our team will take the role of a data analytics group within a music-streaming company that supports playlist marketing managers. These users need to understand how different audio and metadata characteristics of tracks relate to popularity in order to design engaging playlists and communicate data-driven insights to artists and labels.

The goal of our dashboard is to provide an interactive exploration environment for the Spotify catalogue. Managers will be able to visually explore how genres and moods relate to track popularity, and how audio features combine to create successful songs within and across genres. The dashboard will also support discovering tracks that look potentially good from an audio-feature perspective but are not currently very popular.

In short, the app aims to:

1. Help users compare the audio profiles of genres and mood regions.
2. Allow users to identify combinations of features that are consistently associated with high-popularity tracks.
3. Enable users to surface candidates for playlist inclusion by finding tracks that are audio-similar to known hits but have lower current popularity.

By offering interactive visualizations instead of a single static chart, the dashboard is intended to encourage playful exploration while still supporting serious decision-making for playlist strategy and marketing campaigns.


## 2. Description of the Data

We will use the public [Spotify Tracks Dataset](https://www.kaggle.com/datasets/maharshipandya/-spotify-tracks-dataset) compiled by Maharshi Pandya and hosted on Kaggle. The dataset contains approximately 114,000 tracks spanning about 125 genres, each with a set of Spotify audio features and basic metadata.

Each row represents a single track and includes:

#### Identifiers and text fields

- `track_id`: unique Spotify track ID.
- `track_name`: track title.
- `artists`: semicolon-separated list of performing artists.
- `album_name`: album in which the track appears.

#### Outcome and duration

- `popularity`: integer 0–100 describing current track popularity.
- `duration_ms`: track length in milliseconds.

#### Categorical descriptors

- `explicit`: whether the track contains explicit content.
- `track_genre`: assigned genre label.
- `key`: musical key encoded as integers
- `mode`: 1 = major, 0 = minor.
- `time_signature`: estimated meter, from 3 to 7

#### Continuous audio features (0.0–1.0)

- `danceability`, `energy`, `speechiness`, `acousticness`, `instrumentalness`, `liveness`, `valence`
- `tempo`: beats per minute.
- `loudness`: overall loudness in dB.

We plan to derive a small set of additional variables, such as:

- `duration_min` = duration_ms / 60000
- `popularity_tier` (low / medium / high)
- `tempo_band` (slow, medium, fast)
- `mood_quadrant` based on the combination of energy and valence


## 3. Research Questions and Usage Scenarios

### 3.1 Research Questions

1. **How do audio features and popularity vary across genres and moods?**  
   Which genres tend to have the highest average popularity? Are upbeat tracks more popular overall than chill tracks? How do explicit vs non-explicit tracks differ in energy, tempo, and popularity distributions?

2. **Within a given genre, what combinations of audio features characterize hit songs compared with less popular tracks?**  
   We will compare high-popularity tracks to medium/low-popularity ones within the same genre, focusing on features such as danceability, energy, tempo, valence, and acousticness. The dashboard will support quickly switching genres and observing how the hit profile changes.

3. **How can users discover songs that resemble successful songs in audio space but are not yet very popular?**  
   For a selected reference track (well-known ones), we want to surface tracks with similar audio-feature profiles but lower popularity. This can help curators find fresh songs that fit a desired sound while diversifying their playlists.

### 3.2 Usage Scenario

Z is a playlist editor responsible for maintaining several editorial playlists. Z wants to both understand what currently works in each playlist and discover new tracks that fit the desired mood.

When Z uses our dashboard, they see an overview scatterplot of tracks, with energy on the x-axis and valence on the y-axis, colored by track_genre and sized by popularity.

On the left, a control panel allows Z to filter by track_genre (multi-select), explicit flag, tempo_band, and popularity_tier. Z can select a mood region by brushing over the scatterplot (high-energy, high-valence songs). In addition to using the filter controls, Z can also use a search bar to quickly filter tracks by keywords such as track name, artist, or album, making it easier to locate specific items within large selections.

Once Z applies a filter and brush, a genre summary panel updates, showing bar charts of average popularity and danceability per genre for the currently selected tracks. A feature distribution panel (faceted histograms or density plots) shows how tempo, loudness, and duration are distributed for the selection. A track list panel at the bottom displays a sortable table with track name, artist, genre, popularity, and key features.

If Z wants to explicitly compare different groups of tracks (e.g., across genres or popularity tiers), Z can enter a compare mode and add multiple selected groups or reference tracks. The feature distribution panel then displays these groups side by side, allowing Z to directly compare their audio profiles.

If Z clicks on a specific popular track in the table or scatterplot, a side panel highlights similar tracks based on their audio features but with lower popularity tiers. Z can then mark some of these tracks as candidates and export a list to use when updating playlists.

This scenario motivates our design choices: multiple coordinated views, strong filtering capabilities, and the ability to move seamlessly from high-level patterns (which genres dominate a mood region) to track-level decisions (which songs to add next).
