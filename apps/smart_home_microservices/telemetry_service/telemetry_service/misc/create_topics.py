#!/usr/bin/env python3
import os
import sys
from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka import KafkaException

KAFKA_TOPICS_AT_STARTUP = ["sensor_status_events"]


def main():
    # 1. Connect to Kafka
    admin_conf = {"bootstrap.servers": os.getenv("KAFKA_URL", "localhost:9092")}
    admin = AdminClient(admin_conf)

    # 2. List existing topics
    try:
        md = admin.list_topics(timeout=10)
    except KafkaException as e:
        print(f"Failed to fetch metadata: {e}", file=sys.stderr)
        sys.exit(1)

    existing_topics = set(md.topics.keys())
    print("Existing topics:")
    for t in sorted(existing_topics):
        print(f"  • {t}")

    # 3. Create any missing topics
    new_topics = []
    for t in KAFKA_TOPICS_AT_STARTUP:
        if t not in existing_topics:
            # adjust partitions/replication as needed
            new_topics.append(NewTopic(topic=t))

    if new_topics:
        print("\nCreating missing topics...")
        fs = admin.create_topics(new_topics)
        # wait for each operation to finish
        for topic, f in fs.items():
            try:
                f.result()  # The result itself is None
                print(f"  ✔ Created topic {topic}")
            except Exception as e:
                # If it already exists, that’s fine; otherwise show error
                print(f"  ✘ Failed to create {topic}: {e}", file=sys.stderr)
    else:
        print("\nAll desired topics already exist.")


if __name__ == "__main__":
    main()
