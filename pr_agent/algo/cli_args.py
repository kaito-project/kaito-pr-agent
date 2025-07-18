# Copyright (c) 2023 PR-Agent Authors
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import hashlib
from base64 import b64decode, b64encode, encode


class CliArgs:
    @staticmethod
    def validate_user_args(args: list) -> (bool, str):
        try:
            if not args:
                return True, ""

            # decode forbidden args
            # b64encode('word'.encode()).decode()
            _encoded_args = 'c2hhcmVkX3NlY3JldA==:dXNlcg==:c3lzdGVt:ZW5hYmxlX2NvbW1lbnRfYXBwcm92YWw=:ZW5hYmxlX21hbnVhbF9hcHByb3ZhbA==:ZW5hYmxlX2F1dG9fYXBwcm92YWw=:YXBwcm92ZV9wcl9vbl9zZWxmX3Jldmlldw==:YmFzZV91cmw=:dXJs:YXBwX25hbWU=:c2VjcmV0X3Byb3ZpZGVy:Z2l0X3Byb3ZpZGVy:c2tpcF9rZXlz:b3BlbmFpLmtleQ==:QU5BTFlUSUNTX0ZPTERFUg==:dXJp:YXBwX2lk:d2ViaG9va19zZWNyZXQ=:YmVhcmVyX3Rva2Vu:UEVSU09OQUxfQUNDRVNTX1RPS0VO:b3ZlcnJpZGVfZGVwbG95bWVudF90eXBl:cHJpdmF0ZV9rZXk=:bG9jYWxfY2FjaGVfcGF0aA==:ZW5hYmxlX2xvY2FsX2NhY2hl:amlyYV9iYXNlX3VybA==:YXBpX2Jhc2U=:YXBpX3R5cGU=:YXBpX3ZlcnNpb24=:c2tpcF9rZXlz'

            forbidden_cli_args = []
            for e in _encoded_args.split(':'):
                forbidden_cli_args.append(b64decode(e).decode())

            # lowercase all forbidden args
            for i, _ in enumerate(forbidden_cli_args):
                forbidden_cli_args[i] = forbidden_cli_args[i].lower()
                if '.' not in forbidden_cli_args[i]:
                    forbidden_cli_args[i] = '.' + forbidden_cli_args[i]

            for arg in args:
                if arg.startswith('--'):
                    arg_word = arg.lower()
                    arg_word = arg_word.replace('__', '.')  # replace double underscore with dot, e.g. --openai__key -> --openai.key
                    for forbidden_arg_word in forbidden_cli_args:
                        if forbidden_arg_word in arg_word:
                            return False, forbidden_arg_word
            return True, ""
        except Exception as e:
            return False, str(e)
