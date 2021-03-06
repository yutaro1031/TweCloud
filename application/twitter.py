import json
from urllib.parse import parse_qsl
from flask import request
from requests_oauthlib import OAuth1Session
import application.config as config

consumer_key = config.TWITTER_CONSUMER_KEY
consumer_secret = config.TWITTER_CONSUMER_SECRET
# AT = config.ACCESS_TOKEN
# ATS = config.ACCESS_TOKEN_SECRET

base_url = 'https://api.twitter.com/'
request_token_url = base_url + 'oauth/request_token'
authenticate_url = base_url + 'oauth/authenticate'
access_token_url = base_url + 'oauth/access_token'
get_tweet_url = base_url + '1.1/statuses/user_timeline.json'
post_tweet_url = base_url + '1.1/statuses/update.json'
upload_media_url = 'https://upload.twitter.com/1.1/media/upload.json'

# ツイートを取得
def get_tweets(access_token):
    loop_count = 0
    max_id = None
    tweet_list = []

    params = {
        'count': 200,
        'user_id': request.args.get('user_id'),
        'max_id': None,
        'exclude_replies': True,
        'include_rts': False
    }
    twitter = OAuth1Session(
        consumer_key,
        consumer_secret,
        access_token['oauth_token'],
        access_token['oauth_token_secret'],
    )

    while True: # max_idが一番古いIDになるまで繰り返す
        print('%d番目のリクエスト' % loop_count, max_id)
        new_tweet_list = []
        params['max_id'] = max_id # paramsの更新
        response = twitter.get(get_tweet_url, params=params)

        if response.status_code == 200:
            timeline = json.loads(response.text)
            new_max_id = timeline[-1]['id']

            # jsonデータからツイートを取得
            for tweet in timeline:
                new_tweet_list.append(tweet['text'])

            # 最後の取得ツイートのidが前回取得時のそれと同等か
            if max_id != new_max_id:
                new_tweet_list.pop(-1) # 最後の要素を削除(次のループで追加されるため)
                tweet_list.extend(new_tweet_list)
                max_id = new_max_id
                loop_count += 1
            else:
                tweet_list.extend(new_tweet_list)
                break

        else:
            print("ツイート取得失敗: %d" % response.status_code)
            return False

    # ループ終了後
    print('取得ツイート数', len(tweet_list))
    return tweet_list


# 認証画面（「このアプリと連携しますか？」の画面）のURLを返すAPI
def get_request_token():

    # Twitter Application Management で設定したコールバックURLsのどれか
    oauth_callback = request.args.get('oauth_callback')
    twitter = OAuth1Session(consumer_key, consumer_secret)
    response = twitter.post(
        request_token_url,
        params={'oauth_callback': oauth_callback}
    )

    if response.status_code != 200:
        print ("リクエストトークン取得失敗: %s", response.text)
        return None

    request_token = dict(parse_qsl(response.content.decode("utf-8")))

    # リクエストトークンから認証画面のURLを生成
    authenticate_endpoint = '%s?oauth_token=%s' \
        % (authenticate_url, request_token['oauth_token'])

    return authenticate_endpoint


# アクセストークン（連携したユーザーとしてTwitterのAPIを叩くためのトークン）を返すAPI
def get_access_token(oauth_token, oauth_verifier):

    twitter = OAuth1Session(
        consumer_key,
        consumer_secret,
        oauth_token,
        oauth_verifier,
    )
    response = twitter.post(
        access_token_url,
        params={'oauth_verifier': oauth_verifier}
    )

    if response.status_code != 200:
        print ("アクセストークン取得失敗: %s", response.text)
        return False

    access_token = dict(parse_qsl(response.content.decode("utf-8")))

    return access_token


# シェア機能
def tweet_with_image(oauth_token, oauth_token_secret, tweet_text, file_path):

    twitter = OAuth1Session(
        consumer_key,
        consumer_secret,
        oauth_token,
        oauth_token_secret,
    )
    files = {"media" : open(file_path, 'rb')}
    req_media = twitter.post(upload_media_url, files = files)

    # レスポンスを確認
    if req_media.status_code != 200:
        print ("画像アップデート失敗: %s", req_media.text)
        return False
    
    # Media ID を取得
    media_id = json.loads(req_media.text)['media_id']
    print ("Media ID: %d" % media_id)

    # Media ID を付加してテキストを投稿
    params = {'status': tweet_text, "media_ids": [media_id]}
    req_media = twitter.post(post_tweet_url, params = params)

    # 再びレスポンスを確認
    if req_media.status_code != 200:
        print ("テキストアップデート失敗: %s", tweet_text)
        return False

    return True


# 文字列を結合
def conbine_tweets(tweet_list):
    return ''.join(tweet_list)