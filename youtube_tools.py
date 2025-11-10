import re
import json
from googleapiclient.discovery import Resource
from pydantic import BaseModel, Field
from tools.google.google_apis import create_service

class PlaylistInfo(BaseModel):
    playlist_id: str = Field(..., description='Playlist ID')
    playlist_title: str = Field(..., description='Playlist Title')
    channel_id: str = Field(..., description='Channel ID')
    description: str = Field(..., description='Playlist Description')
    published_at: str = Field(..., description='Playlist Published Time')

class PlaylistResults(BaseModel):
    total_results: int = Field(..., description='Total number of results')
    playlists: list[PlaylistInfo] = Field(..., description='Playlist Information')

class ChannelInfo(BaseModel):
    channel_id: str = Field(..., description='Channel ID')
    channel_title: str = Field(..., description='Channel Title')
    description: str = Field(..., description='Channel Description')
    published_at: str = Field(..., description='Channel Published Time')
    country: str = Field(None, description='Channel Country')
    view_count: int = Field(None, description='View Count')
    subscriber_count: int = Field(None, description='Subscriber Count')
    video_count: int = Field(None, description='Video Count')

class ChannelResults(BaseModel):
    total_results: int = Field(..., description='Total number of results')
    channels: list[ChannelInfo] = Field(..., description='Channel Information')

class VideoInfo(BaseModel):
    channel_id: str = Field(..., description='Channel ID')
    channel_title: str = Field(..., description='Channel Title')
    video_id: str = Field(..., description='Video ID')
    video_title: str = Field(..., description='Video Title')
    description: str = Field(..., description='Video Description')
    published_at: str = Field(..., description='Video Published Time')

    # Additional Information (optional)
    tags: list[str] = Field(None, description='Video Tags')
    duration: str = Field(None, description='Video Duration')
    dimension: str = Field(None, description='Video Dimension')
    view_count: int = Field(None, description='View Count')
    like_count: int = Field(None, description='Like Count')
    comment_count: int = Field(None, description='Comment Count')  # default to 0 to avoid type error
    topic_categories: list[str] = Field(None, description='Topic Categories')
    has_paid_product_placement: bool = Field(None, description='Has Paid Product Placement')

class VideoResults(BaseModel):
    total_results: int = Field(..., description='Total number of results')
    videos: list[VideoInfo] = Field(..., description='Video Information')

def extract_video_id(input_str: str) -> str | None:
    """
    Extract YouTube video ID from a URL or ID string.

    Args:
        input_str: URL or ID string to extract video ID from.

    Returns:
        str: Extracted YouTube video ID.
    """
    url_pattern = re.compile(
        r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})'
    )
    match = url_pattern.match(input_str)

    if match:
        return match.group(1)

    id_pattern = re.compile(r'^[a-zA-Z0-9_-]{11}$')
    if id_pattern.match(input_str):
        return input_str

    return None

class YouTubeTool:
    """  
    Toolkit for interacting with the YouTube Data API.

    Based on https://developers.google.com/youtube/v3/docs
    """
    API_NAME = 'youtube'
    API_VERSION = 'v3'
    SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']

    def __init__(
        self, 
        client_secret: str
    ) -> None:
        self.client_secret = client_secret
        self._init_youtube_service()

    def _init_youtube_service(self):
        """
        Initialize the YouTube Data API service.
        """
        self.service = create_service(
            self.client_secret,
            self.API_NAME,
            self.API_VERSION,
            self.SCOPES
        )
        if not self.service:
            raise Exception("Failed to create YouTube service")

    @property
    def youtube_service(self) -> Resource:
        """
        Return YouTube Data API service instance.
        """
        return self.service
    
    def get_channel_info(
        self, 
        channel_id: str
    ) -> str:
        """
        Get information about a YouTube channel based on the provided channel ID.

        Args:
            channel_id (str): The ID of the YouTube channel.
        
        Returns:
            str: Information about the YouTube channel.
        """
        if channel_id.startswith('UC'):
            request = self.service.channels().list(
                part='snippet,statistics',
                id=channel_id
            )
        elif channel_id.startswith('@'):
            request = self.service.channels().list(
                part='snippet,statistics',
                forHandle=channel_id
            )
        else:
            return 'Invalid channel ID'
        
        response = request.execute()

        channel_info = ChannelInfo(
            channel_id=response['items'][0].get('id'),
            channel_title=response['items'][0]['snippet'].get('title'),
            description=response['items'][0]['snippet'].get('description'),
            published_at=response['items'][0]['snippet'].get('publishedAt'),
            country=response['items'][0]['snippet'].get('country', ''),
            view_count=response['items'][0]['statistics'].get('viewCount'),
            subscriber_count=response['items'][0]['statistics'].get('subscriberCount'),
            video_count=response['items'][0]['statistics'].get('videoCount')
        )
        return channel_info.model_dump_json()
    
    def search_channel(
        self, 
        channel_name: str,  
        published_after: str = None, 
        published_before: str = None, 
        region_code: str = 'US', 
        order: str = 'relevance', 
        max_results: int = 50
    ) -> str:
        """
        Searches for YouTube channels based on the provided channel name.
        
        Args:
            channel_name (str): The name of the channel to search for.
            published_after (str): The publishedAfter parameter indicates that the API response 
                should only contain resources created at or after the specified time. 
                The value is an RFC 3339 formatted date-time value (1970-01-01T00:00:00Z).
            published_before (str): The publishedBefore parameter indicates that the API response 
                should only contain resources created before or at the specified time. 
                The value is an RFC 3339 formatted date-time value (1970-01-01T00:00:00Z).
            region_code (str): The regionCode parameter instructs the API to return search results 
                for the specified country. The parameter value is an ISO 3166-1 alpha-2 country code.
            order (str): The order in which to return results. Default is 'relevance'. 
                Options include 'date', 'rating', 'relevance', 'title', 'videoCount', and 'viewCount'.
            max_results (int): The maximum number of results to return. Default is 50.

        Returns:
            str: A list of channels that match the search
        """
        lst = []
        total_results = 0
        next_page_token = None

        while len(lst) < max_results:
            current_max = min(50, max_results - len(lst))
            
            request = self.service.search().list(
                part='snippet',
                q=channel_name,
                type='channel',
                maxResults=current_max,
                order=order,
                publishedAfter=published_after,
                publishedBefore=published_before,
                regionCode=region_code,
                pageToken=next_page_token
            )
            response = request.execute()

            for item in response['items']:
                channel_id = item['id'].get('channelId')
                channel_title = item['snippet'].get('title')
                channel_description = item['snippet'].get('description')
                channel_published_at = item['snippet'].get('publishedAt')
                channel_info = ChannelInfo(
                    channel_id=channel_id,
                    channel_title=channel_title,
                    description=channel_description,
                    published_at=channel_published_at
                )
                lst.append(channel_info)

            total_results = response['pageInfo']['totalResults']
            next_page_token = response.get('nextPageToken')

            if not next_page_token:
                break
        
        return ChannelResults(
            total_results=total_results,
            channels=lst
        ).model_dump_json()

    def search_playlist(
        self, 
        query: str, 
        published_after: str = None, 
        published_before: str = None, 
        region_code: str = 'US', 
        order: str = 'date', 
        max_results: int = 50
    ) -> str:
        """
        Searches for YouTube playlists based on the provided query.

        Args:
            query (str): The query to search for.
            published_after (str): The publishedAfter parameter indicates that the API response 
                should only contain resources created at or after the specified time. 
                The value is an RFC 3339 formatted date-time value (1970-01-01T00:00:00Z).
            published_before (str): The publishedBefore parameter indicates that the API response 
                should only contain resources created before or at the specified time. 
                The value is an RFC 3339 formatted date-time value (1970-01-01T00:00:00Z).
            region_code (str): The regionCode parameter instructs the API to return search results 
                for the specified country. The parameter value is an ISO 3166-1 alpha-2 country code.
            order (str): The order in which to return results. Default is 'date'. 
                Options include 'date', 'rating', 'relevance', 'title', 'videoCount', and 'viewCount'.
            max_results (int): The maximum number of results to return. Default is 50.

        Returns:
            str: A list of playlists that match the search
        """
        
        lst = []
        total_results = 0
        next_page_token = None

        while len(lst) < max_results:
            current_max = min(50, max_results - len(lst))
            
            request = self.service.search().list(
                part='snippet',
                q=query,
                type='playlist',
                maxResults=current_max,
                order=order,
                publishedAfter=published_after,
                publishedBefore=published_before,
                regionCode=region_code,                
                pageToken=next_page_token
            )
            response = request.execute()

            for item in response['items']:
                playlist_id = item['id'].get('playlistId')
                playlist_title = item['snippet'].get('title')
                channel_id = item['snippet'].get('channelId')
                playlist_description = item['snippet'].get('description')
                playlist_published_at = item['snippet'].get('publishedAt')
                playlist_info = PlaylistInfo(
                    playlist_id=playlist_id,
                    playlist_title=playlist_title,
                    channel_id=channel_id,
                    description=playlist_description,
                    published_at=playlist_published_at
                )
                lst.append(playlist_info)

            total_results = response['pageInfo']['totalResults']
            next_page_token = response.get('nextPageToken')

            if not next_page_token:
                break

        return PlaylistResults(
            total_results=total_results,
            playlists=lst
        ).model_dump_json()

    def search_videos(
        self, 
        query: str,  
        published_after: str = None, 
        published_before: str = None, 
        region_code: str = 'US', 
        video_duration: str = 'any', 
        order: str = 'date', 
        max_results: int = 50
    ) -> str:
        """
        Searches for YouTube videos based on the provided query.

        Args:
            query (str): The query to search for.
            published_after (str): The publishedAfter parameter indicates that the API response 
                should only contain resources created at or after the specified time. 
                The value is an RFC 3339 formatted date-time value (1970-01-01T00:00:00Z).
            published_before (str): The publishedBefore parameter indicates that the API response 
                should only contain resources created before or at the specified time. 
                The value is an RFC 3339 formatted date-time value (1970-01-01T00:00:00Z).
            region_code (str): The regionCode parameter instructs the API to return search results 
                for the specified country. The parameter value is an ISO 3166-1 alpha-2 country code.
            video_duration (str): The videoDuration parameter filters video search results based on their duration. 
                Default is 'Any'. Options include 'any', 'long', 'medium', 'short'.
            order (str): The order in which to return results. Default is 'date'. 
                Options include 'date', 'rating', 'relevance', 'title', 'videoCount', and 'viewCount'.
            max_results (int): The maximum number of results to return. Default is 50.

        Returns:
            str: A list of videos that match the search
        """
        
        lst = []
        total_results = 0
        next_page_token = None

        while len(lst) < max_results:
            current_max = min(50, max_results - len(lst))
            
            request = self.service.search().list(
                part='snippet',
                q=query,
                type='video',
                maxResults=current_max,
                order=order,
                publishedAfter=published_after,
                publishedBefore=published_before,
                regionCode=region_code,
                videoDuration=video_duration,
                pageToken=next_page_token
            )
            response = request.execute()

            for item in response['items']:
                channel_id = item['snippet'].get('channelId')
                channel_title = item['snippet'].get('channelTitle')
                video_id = item['id'].get('videoId')
                video_title = item['snippet'].get('title')
                video_description = item['snippet'].get('description')
                video_published = item['snippet'].get('publishTime')
                video_info = VideoInfo(
                    channel_id=channel_id,
                    channel_title=channel_title,
                    video_id=video_id,
                    video_title=video_title,
                    description=video_description,
                    published_at=video_published
                )
                lst.append(video_info)

            total_results = response['pageInfo']['totalResults']
            next_page_token = response.get('nextPageToken')

            if not next_page_token:
                break

        return VideoResults(
            total_results=total_results,
            videos=lst
        ).model_dump_json()
    
    def get_video_info(
        self, 
        video_ids: str, 
        max_results: int = 50
    ) -> str:
        """
        Retrieves detailed information about YouTube videos based on the provided video IDs.

        Args:
            video_ids (str): A comma-separated string of video IDs.
            max_results (int): The maximum number of results to return. Default is 50.

        Returns:
            str: A list of videos with detailed information
        """
        if len(video_ids) == 1:
            video_ids = extract_video_id(video_ids)
            if not video_ids:
                return 'Error: Invalid video ID or URL.'
        
        lst = []
        total_results = 0
        next_page_token = None

        while len(lst) < max_results:
            current_max = min(50, max_results - len(lst))
            
            request = self.service.videos().list(
                part='id,snippet,contentDetails,statistics,paidProductPlacementDetails,topicDetails', 
                id=video_ids,
                maxResults=current_max,
                pageToken=next_page_token
            )
            response = request.execute()

            for item in response['items']:
                snippet = item['snippet']
                content_details = item.get('contentDetails', {})
                statistics = item.get('statistics', {})
                topic_details = item.get('topicDetails', {})

                video_info = VideoInfo(
                    channel_id=snippet['channelId'],
                    channel_title=snippet['channelTitle'],
                    video_id=item['id'],
                    video_title=snippet['title'],
                    description=snippet.get('description', ''),
                    published_at=snippet['publishedAt'],
                    tags=snippet.get('tags', []),
                    duration=content_details.get('duration'),
                    dimension=content_details.get('dimension'),
                    view_count=statistics.get('viewCount'),
                    like_count=statistics.get('likeCount', 0),
                    comment_count=statistics.get('commentCount', 0),
                    topic_categories=topic_details.get('topicCategories', []),
                    has_paid_product_placement=snippet.get('hasPaidPromotion', False)
                )
                lst.append(video_info)

            total_results = response['pageInfo']['totalResults']
            next_page_token = response.get('nextPageToken')

            if not next_page_token:
                break

        return VideoResults(
            total_results=total_results,
            videos=lst
        ).model_dump_json()

    def get_channel_videos(
        self, 
        channel_id: str, 
        max_results: int = 50
    ) -> str:
        """
        Return videos uploaded by a YouTube channel based on the provided channel ID.

        Args:
            channel_id (str): The ID of the YouTube channel.
            max_results (int): The maximum number of results to return. Default is 50.

        Returns:
            str: A list of videos uploaded by the channel
        """
        
        lst = []
        total_results = 0
        next_page_token = None

        while len(lst) < max_results:
            request = self.service.channels().list(
                part='contentDetails',
                id=channel_id
            )
            response = request.execute()

            uploads_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists'].get('uploads')

            current_max = min(50, max_results - len(lst))
            
            playlist_request = self.service.playlistItems().list(
                part='snippet',
                playlistId=uploads_playlist_id,
                maxResults=current_max,
                pageToken=next_page_token
            )
            playlist_response = playlist_request.execute()

            for item in playlist_response['items']:
                snippet = item['snippet']

                video_info = VideoInfo(
                    channel_id=snippet['channelId'],
                    channel_title=snippet['channelTitle'],
                    video_id=snippet['resourceId']['videoId'],
                    video_title=snippet['title'],
                    description=snippet.get('description', ''),
                    published_at=snippet['publishedAt'],
                )
                lst.append(video_info)

            total_results = playlist_response['pageInfo']['totalResults']
            next_page_token = playlist_response.get('nextPageToken')

            if not next_page_token:
                break

        return VideoResults(
            total_results=total_results,
            videos=lst
        ).model_dump_json()
    
    def construct_hyperlinke(
        self, 
        id: str, 
        type: str
    ) -> str:
        """
        Construct a hyperlink based on the provided ID and type.

        Args:
            id (str): The ID of the YouTube resource.
            type (str): The type of the YouTube resource. Options include 'channel', 'playlist', and 'video'.

        Returns:
            str: The hyperlink to the YouTube resource.
        """
        if type == 'channel':
            link = f'https://www.youtube.com/channel/{id}'
        elif type == 'playlist':
            link = f'https://www.youtube.com/playlist?list={id}'
        elif type == 'video':
            link = f'https://www.youtube.com/watch?v={id}'
        else:
            link = ''
            
        return link