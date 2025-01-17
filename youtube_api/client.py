from copy import deepcopy
import logging
import requests

from .exceptions import *
from .classes import *


ENDPOINT = "https://www.googleapis.com/youtube/v3/{resource_type}"

logger = logging.getLogger(__name__)

class Client(object):
    """
    Generic class with common methods, not to be called directly
    """
    def __init__(self, api_key):
        self.api_key = api_key
        self.resource_type = None
        self.allowed_parts = None
        self.allowed_filters = None
        self.allowed_optional_params = None

    def get_resource(self, resource_filter, parts, optional_params):
        """
        Low level generic method to get resource, used by other methods that add specific params for each resource

        :param resource_type: string with resource type to create the complete endpoint
        :param resource_filter: dictionary with the filter to be used
        :param parts: dictionary with the parts to be returned
        :param optional_params: dictionary with all the params
        :return: requests response object
        """
        ERRORS_MAPPING = {
            400: YouTubeBadRequest,
            403: YouTubeForbidden,
            404: YoutubeNotFound
        }

        params = self.digest_request_params(resource_filter, parts, optional_params)

        url = ENDPOINT.format(resource_type=self.resource_type)
        params.update({'key': self.api_key})
        response = requests.get(url, params=params)

        if response.status_code in ERRORS_MAPPING:
            raise ERRORS_MAPPING[response.status_code](response.json()["error"]["errors"][0]["reason"])
        return response

    def authorize(self):
        SCOPES = {
            'general': 'https://www.googleapis.com/auth/youtube',
            'channel': 'https://www.googleapis.com/auth/youtube.force-ssl',
            'view': 'https://www.googleapis.com/auth/youtube.readonly',
            'video': 'https://www.googleapis.com/auth/youtube.upload',
            'assets': 'https://www.googleapis.com/auth/youtubepartner',
            'audit': 'https://www.googleapis.com/auth/youtubepartner-channel-audit'
        }
        pass

    def get_auth_resource(self, resource_filter, parts, optional_params):
        """
        Low level generic method to get resource, used by other methods that add specific params for each resource
        with authorization before request

        :param resource_type: string with resource type to create the complete endpoint
        :param resource_filter: dictionary with the filter to be used
        :param parts: dictionary with the parts to be returned
        :param optional_params: dictionary with all the params
        :return: requests response object
        """

        ERRORS_MAPPING = {
            400: YouTubeBadRequest,
            403: YouTubeForbidden,
            404: YoutubeNotFound
        }

        params = self.digest_request_params(resource_filter, parts, optional_params)

        url = ENDPOINT.format(resource_type=self.resource_type)
        params.update({'key': self.api_key})
        self.authorize()
        response = requests.get(url, params=params, headers={"Authorization": self.access_token})

        if response.status_code in ERRORS_MAPPING:
            raise ERRORS_MAPPING[response.status_code](response.json()["error"]["errors"][0]["reason"])
        return response

    def post_resource(self, parts, optional_params):
        """
        Low level generic method to post resource, used by other methods that add specific params for each resource

        :param parts: dictionary with the parts to be returned
        :param optional_params: dictionary with all the params
        :return: requests response object
        """
        ERRORS_MAPPING = {
            400: YouTubeBadRequest,
            403: YouTubeForbidden,
            404: YoutubeNotFound
        }

        params = {'part': ','.join(parts)}
        params.update(optional_params)

        url = ENDPOINT.format(resource_type=self.resource_type)
        params.update({'key': self.api_key})
        response = requests.post(url, params=params)

        if response.status_code in ERRORS_MAPPING:
            raise ERRORS_MAPPING[response.status_code](response.json()["error"]["errors"][0]["reason"])
        return response

    def digest_request_params(self, resource_filter, parts, optional_params):
        self.validate_resource_filter(resource_filter)
        self.validate_parts(parts)
        if optional_params:
            self.validate_optional_params(optional_params)

        # if validation passes
        params = {'part': ','.join(parts)}
        params.update(resource_filter)
        params.update(optional_params)

        return params

    def validate_resource_filter(self, resource_filter):
        resource_filter_keys = resource_filter.keys()

        if len(resource_filter_keys) > 1:
            raise OneFilterAllowed('YouTube allows one filter per request only')

        intersection = self.allowed_filters & frozenset(resource_filter_keys)

        if not intersection:
             raise FilterNotAllowed('{0} is not an allowed filter'.format(resource_filter.keys()))



    def validate_parts(self, parts):
        frozen_parts = frozenset(parts) # free in Python 3.x
        frozen_allowed_parts = frozenset(self.allowed_parts.keys()) # free in Python 3.x
        intersection = frozen_parts & frozen_allowed_parts

        if not intersection:
            not_allowed_parts = frozen_allowed_parts - frozen_parts
            raise PartNotAllowed('{0} not allowed part(s)'.format(', '.join(not_allowed_parts)))

    def validate_optional_params(self, optional_params):
        frozen_params = frozenset(optional_params.keys())
        frozen_allowed_params = frozenset(self.allowed_optional_params)
        intersection = frozen_params & frozen_allowed_params

        if not intersection:
            not_allowed_params = frozen_allowed_params - frozen_params
            raise OptionalParamNotAllowed('{0} not allowed param(s)'.format(', '.join(not_allowed_params)))


class VideoAPI(Client):
    """
    Videos endpoint specific client https://developers.google.com/youtube/v3/docs/videos/
    """
    def __init__(self, api_key):
        super(VideoAPI, self).__init__(api_key)
        self.resource_type = 'videos'
        self.allowed_parts = {'contentDetails': 2,
                              'fileDetails': 1,
                              'id': 0,
                              'liveStreamingDetails': 2,
                              'player': 0,
                              'processingDetails': 1,
                              'recordingDetails': 2,
                              'snippet': 2,
                              'statistics': 2,
                              'status': 2,
                              'suggestions': 1,
                              'topicDetails': 2}
        self.allowed_filters = frozenset(('chart',
                                'id',
                                'myRating'))
        self.allowed_optional_params = frozenset(('maxResults',
                                        'onBehalfOfContentOwner',
                                        'pageToken',
                                        'regionCode',
                                        'videoCategoryId'))

    def calculate_quota(self, parts):
        """
        Returns the quota used for the
        :param parts: Parts to be checked
        :return: Quota used
        """
        return sum((self.allowed_parts[part] for part in parts))

    def get_videos(self, resource_filter, parts, optional_params):
        """
        Get info for videos resource

        :param resource_filter: dictionary with one key:value pair only
        :param parts: tuple of strings https://developers.google.com/youtube/v3/getting-started#part
        :param optional_params: dictionary, usually filter params
        :return: serialised json response
        """
        response = self.get_resource(resource_filter, parts, optional_params=optional_params)
        return response.json()

    def get_video_by_id(self, video_id, parts=('snippet',), optional_params={}):
        """
        Returns a video looking up by ID

        :param video_id: string
        :param parts: tuple of strings https://developers.google.com/youtube/v3/getting-started#part
        :param optional_params: dictionary, usually filter params
        :return: serialised json response
        """
        return self.get_videos(resource_filter={'id': video_id}, parts=parts, optional_params=optional_params)

    def get_videos_by_channel_id(self, channel_id, by_time=True):
        """
        Returns a list of comments by channel's ID

        :param channel_id: string
        :param parts: tuple of strings https://developers.google.com/youtube/v3/getting-started#part
        :param optional_params: dictionary, usually filter params
        :return: Iterator of Comment objects
        """
        next = None
        while True:
            try:
                params = {
                    'moderationStatus': 'published',
                    'textFormat': 'plainText',
                    'order': 'time' if by_time else 'relevance',
                    'maxResults': 20
                }
                if next:
                    params['pageToken'] = next
                threads = self.get_commentThreads(
                    resource_filter={'allThreadsRelatedToChannelId': channel_id},
                    parts=('snippet','replies',),
                    optional_params=params
                )
            except:
                break

            next = threads.nextPageToken

            for comment in threads.comments:
                yield comment.topLevelComment

            if not next:
                break


class CommentThreadsAPI(Client):
    """
    CommentThreads endpoint specific client https://developers.google.com/youtube/v3/docs/commentThreads/
    """
    def __init__(self, api_key):
        super(CommentThreadsAPI, self).__init__(api_key)
        self.resource_type = 'commentThreads'
        self.allowed_parts = {
              'id': 0,
              'replies': 2,
              'snippet': 2
        }
        self.allowed_filters = frozenset((
            'allThreadsRelatedToChannelId',
            'channelId',
            'id',
            'videoId'
        ))
        self.allowed_optional_params = frozenset((
            'maxResults',
            'moderationStatus',
            'order',
            'pageToken',
            'searchTerms',
            'textFormat'
        ))

    def calculate_quota(self, parts):
        """
        Returns the quota used for the
        :param parts: Parts to be checked
        :return: Quota used
        """
        return sum((self.allowed_parts[part] for part in parts))

    def get_commentThreads(self, resource_filter, parts=('snippet',), optional_params={}):
        """
        Get a list of comment threads

        :param resource_filter: dictionary with one key:value pair only
        :param parts: tuple of strings https://developers.google.com/youtube/v3/getting-started#part
        :param optional_params: dictionary, usually filter params
        :return: List of Comment objects
        """
        response = self.get_resource(resource_filter, parts, optional_params=optional_params).json()
        comment_threads = CommentThreadList(response)
        return comment_threads

    def post_reply(self, parts=('snippet',), optional_params={}):
        """
        Send a reply

        :param parts: tuple of strings https://developers.google.com/youtube/v3/getting-started#part
        :param optional_params: dictionary, usually filter params
        :return: Comment object or None
        """
        response = self.post_resource(parts, optional_params=optional_params).json()
        try:
            comment = Comment(response)
        except:
            comment = None
        return comment

    def post_comment(self, parts=('snippet',), optional_params={}):
        """
        Send a Top level comment

        :param parts: tuple of strings https://developers.google.com/youtube/v3/getting-started#part
        :param optional_params: dictionary, usually filter params
        :return: CommentThread object or None
        """
        response = self.post_resource(parts, optional_params=optional_params).json()
        print(response)
        try:
            comment = CommentThread(response)
        except:
            comment = None
        return comment

    def get_comments_by_id(self, video_id, by_time=True):
        """
        Returns a list of comments by video's ID

        :param video_id: string
        :param parts: tuple of strings https://developers.google.com/youtube/v3/getting-started#part
        :param optional_params: dictionary, usually filter params
        :return: Iterator of Comment objects
        """
        next = None
        while True:
            try:
                params = {
                    'moderationStatus': 'published',
                    'textFormat': 'plainText',
                    'order': 'time' if by_time else 'relevance',
                    'maxResults': 20
                }
                if next:
                    params['pageToken'] = next
                threads = self.get_commentThreads(
                    resource_filter={'videoId': video_id},
                    parts=('snippet','replies',),
                    optional_params=params
                )
            except:
                break

            next = threads.nextPageToken

            for comment in threads.comments:
                yield comment.topLevelComment

            if not next:
                break


    def send_reply(self, id: str, text: str):
        """
        Send a comment

        :param video_id: string
        :param parts: tuple of strings https://developers.google.com/youtube/v3/getting-started#part
        :param optional_params: dictionary, usually filter params
        :return: Iterator of Comment objects
        """
        params = {
            "snippet": {
                "textOriginal": text,
                "parentId": id
            }
        }

        status = self.post_reply(
            parts=('snippet',),
            optional_params=params
        )
        if not isinstance(status, Comment):
            raise Exception("Can't send a reply")


    def send_comment(self, channel: str, text: str, video: str=None):
        """
        Send a comment

        :param video_id: string
        :param parts: tuple of strings https://developers.google.com/youtube/v3/getting-started#part
        :param optional_params: dictionary, usually filter params
        :return: Iterator of Comment objects
        """
        params = {
            "snippet": {
                "topLevelComment": {
                    "snippet": {
                        "textOriginal": text
                    }
                },
                "channelId": channel
            }
        }
        if video:
            params["snippet"]["videoId"] = video

        status = self.post_comment(
            parts=('snippet',),
            optional_params=params
        )
        print(status)
        if not isinstance(status, CommentThread):
            raise Exception("Can't send a comment")


    def get_comments_by_channel_id(self, channel_id, by_time=True):
        """
        Returns a list of comments by channel's ID

        :param channel_id: string
        :param parts: tuple of strings https://developers.google.com/youtube/v3/getting-started#part
        :param optional_params: dictionary, usually filter params
        :return: Iterator of Comment objects
        """
        next = None
        while True:
            try:
                params = {
                    'moderationStatus': 'published',
                    'textFormat': 'plainText',
                    'order': 'time' if by_time else 'relevance',
                    'maxResults': 20
                }
                if next:
                    params['pageToken'] = next
                threads = self.get_commentThreads(
                    resource_filter={'allThreadsRelatedToChannelId': channel_id},
                    parts=('snippet','replies',),
                    optional_params=params
                )
            except:
                break

            next = threads.nextPageToken

            for comment in threads.comments:
                yield comment.topLevelComment

            if not next:
                break
