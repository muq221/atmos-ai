{
  "nbformat": 4,
  "nbformat_minor": 0,
  "metadata": {
    "colab": {
      "provenance": []
    },
    "kernelspec": {
      "name": "python3",
      "display_name": "Python 3"
    },
    "language_info": {
      "name": "python"
    }
  },
  "cells": [
    {
      "cell_type": "code",
      "execution_count": null,
      "metadata": {
        "colab": {
          "base_uri": "https://localhost:8080/"
        },
        "collapsed": true,
        "id": "9k-zqReqQRbX",
        "outputId": "01d6d979-a284-4b2f-8a74-a996072a5d0b"
      },
      "outputs": [
        {
          "output_type": "stream",
          "name": "stdout",
          "text": [
            "Requirement already satisfied: requests in /usr/local/lib/python3.12/dist-packages (2.32.4)\n",
            "Requirement already satisfied: pandas in /usr/local/lib/python3.12/dist-packages (2.2.2)\n",
            "Requirement already satisfied: charset_normalizer<4,>=2 in /usr/local/lib/python3.12/dist-packages (from requests) (3.4.6)\n",
            "Requirement already satisfied: idna<4,>=2.5 in /usr/local/lib/python3.12/dist-packages (from requests) (3.11)\n",
            "Requirement already satisfied: urllib3<3,>=1.21.1 in /usr/local/lib/python3.12/dist-packages (from requests) (2.5.0)\n",
            "Requirement already satisfied: certifi>=2017.4.17 in /usr/local/lib/python3.12/dist-packages (from requests) (2026.2.25)\n",
            "Requirement already satisfied: numpy>=1.26.0 in /usr/local/lib/python3.12/dist-packages (from pandas) (2.0.2)\n",
            "Requirement already satisfied: python-dateutil>=2.8.2 in /usr/local/lib/python3.12/dist-packages (from pandas) (2.9.0.post0)\n",
            "Requirement already satisfied: pytz>=2020.1 in /usr/local/lib/python3.12/dist-packages (from pandas) (2025.2)\n",
            "Requirement already satisfied: tzdata>=2022.7 in /usr/local/lib/python3.12/dist-packages (from pandas) (2025.3)\n",
            "Requirement already satisfied: six>=1.5 in /usr/local/lib/python3.12/dist-packages (from python-dateutil>=2.8.2->pandas) (1.17.0)\n"
          ]
        }
      ],
      "source": [
        "!pip install requests pandas"
      ]
    },
    {
      "cell_type": "code",
      "source": [
        "import requests\n",
        "\n",
        "API_KEY = \"d5185a5d6c31c9372214dc23b48e34af\"\n",
        "CITY = \"Hyderabad\"\n",
        "\n",
        "url = f\"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric\"\n",
        "\n",
        "response = requests.get(url)\n",
        "data = response.json()\n",
        "\n",
        "print(data)"
      ],
      "metadata": {
        "colab": {
          "base_uri": "https://localhost:8080/"
        },
        "id": "HC8VdxpqVwWi",
        "outputId": "0dd0cc46-bd9a-4339-cd67-77fe9119e117"
      },
      "execution_count": null,
      "outputs": [
        {
          "output_type": "stream",
          "name": "stdout",
          "text": [
            "{'coord': {'lon': 78.4744, 'lat': 17.3753}, 'weather': [{'id': 801, 'main': 'Clouds', 'description': 'few clouds', 'icon': '02d'}], 'base': 'stations', 'main': {'temp': 35.23, 'feels_like': 33.87, 'temp_min': 35.23, 'temp_max': 35.73, 'pressure': 1009, 'humidity': 24, 'sea_level': 1009, 'grnd_level': 946}, 'visibility': 6000, 'wind': {'speed': 4.12, 'deg': 280}, 'clouds': {'all': 20}, 'dt': 1775722864, 'sys': {'type': 1, 'id': 9214, 'country': 'IN', 'sunrise': 1775694879, 'sunset': 1775739629}, 'timezone': 19800, 'id': 1269843, 'name': 'Hyderabad', 'cod': 200}\n"
          ]
        }
      ]
    },
    {
      "cell_type": "code",
      "source": [
        "from datetime import datetime\n",
        "\n",
        "snapshot1 = {\n",
        "    \"temp\": data[\"main\"][\"temp\"],\n",
        "    \"humidity\": data[\"main\"][\"humidity\"],\n",
        "    \"time\": str(datetime.now())\n",
        "}\n",
        "\n",
        "print(snapshot1)"
      ],
      "metadata": {
        "colab": {
          "base_uri": "https://localhost:8080/"
        },
        "id": "FNveE9-EXmnv",
        "outputId": "5fd7cb36-23ee-4a9d-f563-d9d5110e3e22"
      },
      "execution_count": null,
      "outputs": [
        {
          "output_type": "stream",
          "name": "stdout",
          "text": [
            "{'temp': 35.23, 'humidity': 24, 'time': '2026-04-09 08:32:17.704223'}\n"
          ]
        }
      ]
    },
    {
      "cell_type": "code",
      "source": [
        "import pandas as pd\n",
        "\n",
        "df1 = pd.DataFrame([snapshot1])\n",
        "df1.to_csv(\"atmos_snapshot_1.csv\", index=False)"
      ],
      "metadata": {
        "id": "YkvAviKHX2TE"
      },
      "execution_count": null,
      "outputs": []
    },
    {
      "cell_type": "code",
      "source": [
        "response = requests.get(url)\n",
        "data = response.json()"
      ],
      "metadata": {
        "id": "8qcLBQvmb3qs"
      },
      "execution_count": null,
      "outputs": []
    },
    {
      "cell_type": "code",
      "source": [
        "snapshot2 = {\n",
        "    \"temp\": data[\"main\"][\"temp\"],\n",
        "    \"humidity\": data[\"main\"][\"humidity\"],\n",
        "    \"time\": str(datetime.now())\n",
        "}\n",
        "\n",
        "print(snapshot2)"
      ],
      "metadata": {
        "colab": {
          "base_uri": "https://localhost:8080/"
        },
        "id": "oCguJgC2b_dM",
        "outputId": "ceea4467-dd07-46ac-b1f5-5c3e9c766ff5"
      },
      "execution_count": null,
      "outputs": [
        {
          "output_type": "stream",
          "name": "stdout",
          "text": [
            "{'temp': 36.23, 'humidity': 23, 'time': '2026-04-09 08:51:09.921107'}\n"
          ]
        }
      ]
    },
    {
      "cell_type": "code",
      "source": [
        "df2 = pd.DataFrame([snapshot2])\n",
        "df2.to_csv(\"atmos_snapshot_2.csv\", index=False)"
      ],
      "metadata": {
        "id": "47PKRvxZcJ7E"
      },
      "execution_count": null,
      "outputs": []
    },
    {
      "cell_type": "code",
      "source": [
        "temp_drift = snapshot2[\"temp\"] - snapshot1[\"temp\"]\n",
        "humidity_drift = snapshot2[\"humidity\"] - snapshot1[\"humidity\"]\n",
        "\n",
        "print(\"Temp Change:\", temp_drift)\n",
        "print(\"Humidity Change:\", humidity_drift)"
      ],
      "metadata": {
        "colab": {
          "base_uri": "https://localhost:8080/"
        },
        "id": "wBbc7MXfcq7V",
        "outputId": "f661553c-5066-4a56-f4c3-45976871130e"
      },
      "execution_count": null,
      "outputs": [
        {
          "output_type": "stream",
          "name": "stdout",
          "text": [
            "Temp Change: 1.0\n",
            "Humidity Change: -1\n"
          ]
        }
      ]
    },
    {
      "cell_type": "code",
      "source": [
        "def classify(change):\n",
        "    if abs(change) > 5:\n",
        "        return \"HIGH 🚨\"\n",
        "    elif abs(change) > 2:\n",
        "        return \"MODERATE ⚠️\"\n",
        "    else:\n",
        "        return \"LOW ✅\"\n",
        "\n",
        "print(\"Temp Drift Level:\", classify(temp_drift))"
      ],
      "metadata": {
        "colab": {
          "base_uri": "https://localhost:8080/"
        },
        "id": "cPt_1xTIdJ8X",
        "outputId": "48a57d48-925a-4c75-8018-59d34c3a5471"
      },
      "execution_count": null,
      "outputs": [
        {
          "output_type": "stream",
          "name": "stdout",
          "text": [
            "Temp Drift Level: LOW ✅\n"
          ]
        }
      ]
    },
    {
      "cell_type": "code",
      "source": [
        "final_data = {\n",
        "    \"time1\": snapshot1[\"time\"],\n",
        "    \"time2\": snapshot2[\"time\"],\n",
        "    \"temp1\": snapshot1[\"temp\"],\n",
        "    \"temp2\": snapshot2[\"temp\"],\n",
        "    \"temp_drift\": temp_drift,\n",
        "    \"drift_level\": classify(temp_drift)\n",
        "}\n",
        "\n",
        "df_final = pd.DataFrame([final_data])\n",
        "df_final.to_csv(\"engram_final_output.csv\", index=False)\n",
        "\n",
        "print(df_final)"
      ],
      "metadata": {
        "id": "Ulk53cHrdV1d",
        "outputId": "73850582-b39e-4ed9-bd89-f6b5b3da4305",
        "colab": {
          "base_uri": "https://localhost:8080/"
        }
      },
      "execution_count": null,
      "outputs": [
        {
          "output_type": "stream",
          "name": "stdout",
          "text": [
            "                        time1                       time2  temp1  temp2  \\\n",
            "0  2026-04-09 08:32:17.704223  2026-04-09 08:51:09.921107  35.23  36.23   \n",
            "\n",
            "   temp_drift drift_level  \n",
            "0         1.0       LOW ✅  \n"
          ]
        }
      ]
    },
    {
      "cell_type": "code",
      "source": [
        "!pip install firebase-admin"
      ],
      "metadata": {
        "colab": {
          "base_uri": "https://localhost:8080/"
        },
        "id": "KO_m4GrCrYnf",
        "outputId": "e4267849-7140-4812-f09b-96a01a179858"
      },
      "execution_count": 48,
      "outputs": [
        {
          "output_type": "stream",
          "name": "stdout",
          "text": [
            "Requirement already satisfied: firebase-admin in /usr/local/lib/python3.12/dist-packages (6.9.0)\n",
            "Requirement already satisfied: cachecontrol>=0.12.14 in /usr/local/lib/python3.12/dist-packages (from firebase-admin) (0.14.4)\n",
            "Requirement already satisfied: google-api-python-client>=1.7.8 in /usr/local/lib/python3.12/dist-packages (from firebase-admin) (2.193.0)\n",
            "Requirement already satisfied: google-cloud-storage>=1.37.1 in /usr/local/lib/python3.12/dist-packages (from firebase-admin) (3.10.1)\n",
            "Requirement already satisfied: pyjwt>=2.5.0 in /usr/local/lib/python3.12/dist-packages (from pyjwt[crypto]>=2.5.0->firebase-admin) (2.12.1)\n",
            "Requirement already satisfied: httpx==0.28.1 in /usr/local/lib/python3.12/dist-packages (from httpx[http2]==0.28.1->firebase-admin) (0.28.1)\n",
            "Requirement already satisfied: google-api-core<3.0.0dev,>=1.22.1 in /usr/local/lib/python3.12/dist-packages (from google-api-core[grpc]<3.0.0dev,>=1.22.1; platform_python_implementation != \"PyPy\"->firebase-admin) (2.30.1)\n",
            "Requirement already satisfied: google-cloud-firestore>=2.19.0 in /usr/local/lib/python3.12/dist-packages (from firebase-admin) (2.26.0)\n",
            "Requirement already satisfied: anyio in /usr/local/lib/python3.12/dist-packages (from httpx==0.28.1->httpx[http2]==0.28.1->firebase-admin) (4.13.0)\n",
            "Requirement already satisfied: certifi in /usr/local/lib/python3.12/dist-packages (from httpx==0.28.1->httpx[http2]==0.28.1->firebase-admin) (2026.2.25)\n",
            "Requirement already satisfied: httpcore==1.* in /usr/local/lib/python3.12/dist-packages (from httpx==0.28.1->httpx[http2]==0.28.1->firebase-admin) (1.0.9)\n",
            "Requirement already satisfied: idna in /usr/local/lib/python3.12/dist-packages (from httpx==0.28.1->httpx[http2]==0.28.1->firebase-admin) (3.11)\n",
            "Requirement already satisfied: h2<5,>=3 in /usr/local/lib/python3.12/dist-packages (from httpx[http2]==0.28.1->firebase-admin) (4.3.0)\n",
            "Requirement already satisfied: h11>=0.16 in /usr/local/lib/python3.12/dist-packages (from httpcore==1.*->httpx==0.28.1->httpx[http2]==0.28.1->firebase-admin) (0.16.0)\n",
            "Requirement already satisfied: requests>=2.16.0 in /usr/local/lib/python3.12/dist-packages (from cachecontrol>=0.12.14->firebase-admin) (2.32.4)\n",
            "Requirement already satisfied: msgpack<2.0.0,>=0.5.2 in /usr/local/lib/python3.12/dist-packages (from cachecontrol>=0.12.14->firebase-admin) (1.1.2)\n",
            "Requirement already satisfied: googleapis-common-protos<2.0.0,>=1.63.2 in /usr/local/lib/python3.12/dist-packages (from google-api-core<3.0.0dev,>=1.22.1->google-api-core[grpc]<3.0.0dev,>=1.22.1; platform_python_implementation != \"PyPy\"->firebase-admin) (1.73.1)\n",
            "Requirement already satisfied: protobuf<7.0.0,>=4.25.8 in /usr/local/lib/python3.12/dist-packages (from google-api-core<3.0.0dev,>=1.22.1->google-api-core[grpc]<3.0.0dev,>=1.22.1; platform_python_implementation != \"PyPy\"->firebase-admin) (5.29.6)\n",
            "Requirement already satisfied: proto-plus<2.0.0,>=1.22.3 in /usr/local/lib/python3.12/dist-packages (from google-api-core<3.0.0dev,>=1.22.1->google-api-core[grpc]<3.0.0dev,>=1.22.1; platform_python_implementation != \"PyPy\"->firebase-admin) (1.27.2)\n",
            "Requirement already satisfied: google-auth<3.0.0,>=2.14.1 in /usr/local/lib/python3.12/dist-packages (from google-api-core<3.0.0dev,>=1.22.1->google-api-core[grpc]<3.0.0dev,>=1.22.1; platform_python_implementation != \"PyPy\"->firebase-admin) (2.47.0)\n",
            "Requirement already satisfied: grpcio<2.0.0,>=1.33.2 in /usr/local/lib/python3.12/dist-packages (from google-api-core[grpc]<3.0.0dev,>=1.22.1; platform_python_implementation != \"PyPy\"->firebase-admin) (1.80.0)\n",
            "Requirement already satisfied: grpcio-status<2.0.0,>=1.33.2 in /usr/local/lib/python3.12/dist-packages (from google-api-core[grpc]<3.0.0dev,>=1.22.1; platform_python_implementation != \"PyPy\"->firebase-admin) (1.71.2)\n",
            "Requirement already satisfied: httplib2<1.0.0,>=0.19.0 in /usr/local/lib/python3.12/dist-packages (from google-api-python-client>=1.7.8->firebase-admin) (0.31.2)\n",
            "Requirement already satisfied: google-auth-httplib2<1.0.0,>=0.2.0 in /usr/local/lib/python3.12/dist-packages (from google-api-python-client>=1.7.8->firebase-admin) (0.3.1)\n",
            "Requirement already satisfied: uritemplate<5,>=3.0.1 in /usr/local/lib/python3.12/dist-packages (from google-api-python-client>=1.7.8->firebase-admin) (4.2.0)\n",
            "Requirement already satisfied: google-cloud-core<3.0.0,>=1.4.1 in /usr/local/lib/python3.12/dist-packages (from google-cloud-firestore>=2.19.0->firebase-admin) (2.5.1)\n",
            "Requirement already satisfied: google-resumable-media<3.0.0,>=2.7.2 in /usr/local/lib/python3.12/dist-packages (from google-cloud-storage>=1.37.1->firebase-admin) (2.8.2)\n",
            "Requirement already satisfied: google-crc32c<2.0.0,>=1.1.3 in /usr/local/lib/python3.12/dist-packages (from google-cloud-storage>=1.37.1->firebase-admin) (1.8.0)\n",
            "Requirement already satisfied: cryptography>=3.4.0 in /usr/local/lib/python3.12/dist-packages (from pyjwt[crypto]>=2.5.0->firebase-admin) (43.0.3)\n",
            "Requirement already satisfied: cffi>=1.12 in /usr/local/lib/python3.12/dist-packages (from cryptography>=3.4.0->pyjwt[crypto]>=2.5.0->firebase-admin) (2.0.0)\n",
            "Requirement already satisfied: pyasn1-modules>=0.2.1 in /usr/local/lib/python3.12/dist-packages (from google-auth<3.0.0,>=2.14.1->google-api-core<3.0.0dev,>=1.22.1->google-api-core[grpc]<3.0.0dev,>=1.22.1; platform_python_implementation != \"PyPy\"->firebase-admin) (0.4.2)\n",
            "Requirement already satisfied: rsa<5,>=3.1.4 in /usr/local/lib/python3.12/dist-packages (from google-auth<3.0.0,>=2.14.1->google-api-core<3.0.0dev,>=1.22.1->google-api-core[grpc]<3.0.0dev,>=1.22.1; platform_python_implementation != \"PyPy\"->firebase-admin) (4.9.1)\n",
            "Requirement already satisfied: typing-extensions~=4.12 in /usr/local/lib/python3.12/dist-packages (from grpcio<2.0.0,>=1.33.2->google-api-core[grpc]<3.0.0dev,>=1.22.1; platform_python_implementation != \"PyPy\"->firebase-admin) (4.15.0)\n",
            "Requirement already satisfied: hyperframe<7,>=6.1 in /usr/local/lib/python3.12/dist-packages (from h2<5,>=3->httpx[http2]==0.28.1->firebase-admin) (6.1.0)\n",
            "Requirement already satisfied: hpack<5,>=4.1 in /usr/local/lib/python3.12/dist-packages (from h2<5,>=3->httpx[http2]==0.28.1->firebase-admin) (4.1.0)\n",
            "Requirement already satisfied: pyparsing<4,>=3.1 in /usr/local/lib/python3.12/dist-packages (from httplib2<1.0.0,>=0.19.0->google-api-python-client>=1.7.8->firebase-admin) (3.3.2)\n",
            "Requirement already satisfied: charset_normalizer<4,>=2 in /usr/local/lib/python3.12/dist-packages (from requests>=2.16.0->cachecontrol>=0.12.14->firebase-admin) (3.4.6)\n",
            "Requirement already satisfied: urllib3<3,>=1.21.1 in /usr/local/lib/python3.12/dist-packages (from requests>=2.16.0->cachecontrol>=0.12.14->firebase-admin) (2.5.0)\n",
            "Requirement already satisfied: pycparser in /usr/local/lib/python3.12/dist-packages (from cffi>=1.12->cryptography>=3.4.0->pyjwt[crypto]>=2.5.0->firebase-admin) (3.0)\n",
            "Requirement already satisfied: pyasn1<0.7.0,>=0.6.1 in /usr/local/lib/python3.12/dist-packages (from pyasn1-modules>=0.2.1->google-auth<3.0.0,>=2.14.1->google-api-core<3.0.0dev,>=1.22.1->google-api-core[grpc]<3.0.0dev,>=1.22.1; platform_python_implementation != \"PyPy\"->firebase-admin) (0.6.3)\n"
          ]
        }
      ]
    },
    {
      "cell_type": "code",
      "source": [
        "import firebase_admin\n",
        "from firebase_admin import credentials, db\n",
        "\n",
        "# Replace with your JSON filename\n",
        "cred = credentials.Certificate(\"atmosai-muq221-firebase-adminsdk-fbsvc-d2049df055.json\")\n",
        "\n",
        "firebase_admin.initialize_app(cred, {\n",
        "    'databaseURL': 'https://atmosai-muq221-default-rtdb.asia-southeast1.firebasedatabase.app/'\n",
        "})"
      ],
      "metadata": {
        "colab": {
          "base_uri": "https://localhost:8080/"
        },
        "id": "T2BemQ-WriAb",
        "outputId": "752aec05-2b40-42ac-aa88-bbacad46dc4c"
      },
      "execution_count": 50,
      "outputs": [
        {
          "output_type": "execute_result",
          "data": {
            "text/plain": [
              "<firebase_admin.App at 0x7a8539a35ac0>"
            ]
          },
          "metadata": {},
          "execution_count": 50
        }
      ]
    },
    {
      "cell_type": "code",
      "source": [
        "ref = db.reference(\"atmos_data\")\n",
        "\n",
        "ref.push(final_data)\n",
        "\n",
        "print(\"Data sent to Firebase successfully!\")"
      ],
      "metadata": {
        "colab": {
          "base_uri": "https://localhost:8080/"
        },
        "id": "9W-99FwOusmw",
        "outputId": "393fa7b5-8e35-4255-9022-664a51a394e7"
      },
      "execution_count": 52,
      "outputs": [
        {
          "output_type": "stream",
          "name": "stdout",
          "text": [
            "Data sent to Firebase successfully!\n"
          ]
        }
      ]
    }
  ]
}
