import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime
import io


# ------------------- Database Initialization -------------------
DB_FILE = "feedback.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reviewer TEXT NOT NULL,
            team_member TEXT NOT NULL,
            feedback TEXT NOT NULL,
            team TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            date TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            team TEXT NOT NULL,
            assigned_members TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS team_members (
            team TEXT NOT NULL,
            member_name TEXT NOT NULL,
            UNIQUE(team, member_name)
        )
    ''')
    conn.commit()
    conn.close()

# ------------------- Database Interaction Functions -------------------
def add_admin_user():
    """
    Add a default admin user if not already present in the database.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
    admin_exists = c.fetchone()[0]

    if not admin_exists:
        # Add a default admin user with username 'admin' and password 'admin123'
        c.execute("""
            INSERT INTO users (username, password, role, team, assigned_members)
            VALUES (?, ?, ?, ?, ?)
        """, ("admin", "admin123", "admin", "all", ""))
        conn.commit()
    conn.close()

def add_feedback(reviewer, team_member, feedback, team, status):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
        INSERT INTO feedback (reviewer, team_member, feedback, team, status, date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (reviewer, team_member, feedback, team, status, date))
    conn.commit()
    conn.close()

def get_feedbacks(team=None):
    conn = sqlite3.connect(DB_FILE)
    query = "SELECT * FROM feedback"
    params = ()
    if team:
        query += " WHERE team = ?"
        params = (team,)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def update_feedback(feedback_id, new_status, new_feedback):
    """
    Update the feedback status and feedback text in the database.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        UPDATE feedback
        SET status = ?, feedback = ?
        WHERE id = ?
    """, (new_status, new_feedback, feedback_id))
    conn.commit()
    conn.close()


def delete_feedback(feedback_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM feedback WHERE id = ?", (feedback_id,))
    conn.commit()
    conn.close()

def validate_user(username, password):
    """
    Validate the user and retrieve all user details, including assigned_members.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT username, password, role, team, IFNULL(assigned_members, '')
        FROM users
        WHERE LOWER(username) = LOWER(?) AND password = ?
    """, (username, password))
    user = c.fetchone()
    conn.close()
    return user


def check_duplicate_reviewer(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE LOWER(username) = LOWER(?)", (username,))
    count = c.fetchone()[0]
    conn.close()
    return count > 0

def add_user(username, password, role, team, assigned_members):
    if check_duplicate_reviewer(username):
        return False  # Prevent duplicate usernames
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO users (username, password, role, team, assigned_members)
        VALUES (?, ?, ?, ?, ?)
    """, (username, password, role, team, assigned_members))
    conn.commit()
    conn.close()
    return True

def get_users():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM users", conn)
    conn.close()
    return df

def get_team_members(team):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT DISTINCT member_name FROM team_members WHERE team = ?", (team,))
    members = [row[0] for row in c.fetchall()]
    conn.close()
    return members

def delete_user_mapping(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET assigned_members = '' WHERE username = ?", (username,))
    conn.commit()
    conn.close()

def populate_team_members():
    members = {
        "Hawk Force": ["Utsav Chauhan", "Faisal Iqbal", "Sarosh Abdulah Khan", "Vivek Tyagi", "Mohit Bainsla", "Santosh Gupta", "Vivek Kumar", "Rashmi Payasi"],
        "Guarding Tigers": ["Akash Jain", "Rupesh Singh", "Himanshu Mishra", "Vishwas", "Shweta", "Shubham", "Jaideep Khanna", "Dawar Ali", "Nisha", "Varun"],
        "Speed Demons": ["Kapil Arora", "Himanshu Tiwari", "Aman kumar", "Ansh verma", "Jeevan Singh", "Lavnya", "Jyoti Vishwakarna", "Anil kumar"]
    }
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for team, members_list in members.items():
        for member in members_list:
            c.execute("INSERT OR IGNORE INTO team_members (team, member_name) VALUES (?, ?)", (team, member))
    conn.commit()
    conn.close()

# ------------------- Streamlit UI -------------------
def main():
    st.title("One-to-One Feedback Tracker")
    init_db()
    add_admin_user()
    populate_team_members()

    if "user" not in st.session_state:
        st.session_state.user = None

    if st.session_state.user is None:
        st.subheader("Login")
        with st.form(key="login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            if submit:
                user = validate_user(username, password)
                if user:
                    # Save all user details into session state
                    st.session_state.user = {
                        "username": user[0],
                        "role": user[2],
                        "team": user[3],
                        "assigned_members": user[4]  # Add assigned_members here
                    }
                    st.success(f"Welcome, {user[0]}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Try again.")
    else:
        user = st.session_state.user
        st.sidebar.write(f"Logged in as: **{user['username']}** ({user['role']})")
        if st.sidebar.button("Logout"):
            st.session_state.user = None
            st.rerun()

        menu = ["Add Feedback", "View Feedback", "Update/Delete Feedback"]
        if user['role'] == 'admin':
            menu.extend(["Manage Reviewers", "Manage Team Mapping"])

        choice = st.sidebar.selectbox("Menu", menu)

        if choice == "Add Feedback":
            st.subheader("Add Feedback")

            # Select team for admins; reviewers have fixed teams
            team = user['team'] if user['role'] != 'admin' else st.selectbox(
                "Select Team", ["Hawk Force", "Guarding Tigers", "Speed Demons"]
            )

            # Fetch team members based on role
            all_team_members = get_team_members(team)

            if user['role'] == 'reviewer':
                # Get assigned members from session state
                assigned_members = user.get('assigned_members', '').split(",")
                assigned_members_list = [member.strip() for member in assigned_members if member.strip()]
                # Filter to show only assigned team members
                team_members = [member for member in all_team_members if member in assigned_members_list]
            else:
                team_members = all_team_members

            # Show dropdown if team members are available
            if team_members:
                team_member = st.selectbox("Select Team Member", team_members)
                feedback = st.text_area("Feedback Details")
                status = st.selectbox("Status", ["Pending", "In Progress", "Completed"])

                # Submit feedback
                if st.button("Submit Feedback"):
                    add_feedback(user['username'], team_member, feedback, team, status)
                    st.success("Feedback submitted successfully!")
            else:
                st.warning("No team members assigned to you or available for this team.")






        elif choice == "View Feedback":
            st.subheader("View Feedback")
            if user['role'] == 'admin':
                df = get_feedbacks()  # Admin sees all feedback
            else:
                df = get_feedbacks()  # Non-admins see their feedback
                df = df[df['reviewer'] == user['username']]

            if not df.empty:
                st.dataframe(df)

                # Export buttons side by side
                col1, col2 = st.columns(2)

                # Export as Excel using pandas built-in function
                with col1:
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='Feedbacks')
                    buffer.seek(0)

                    st.download_button(
                        label="Export as Excel",
                        data=buffer,
                        file_name="feedbacks.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                # Export as CSV
                with col2:
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Export as CSV",
                        data=csv,
                        file_name="feedbacks.csv",
                        mime="text/csv"
                    )
            else:
                st.warning("No feedback available.")


        elif choice == "Update/Delete Feedback":
            st.subheader("Update/Delete Feedback")
            if user['role'] == 'admin':
                df = get_feedbacks()  # Admin sees all feedback
            else:
                df = get_feedbacks()  # Non-admins see their feedback
                df = df[df['reviewer'] == user['username']]

            if not df.empty:
                grouped = df.groupby(['team_member', 'reviewer'])
                selected_group = st.selectbox(
                    "Select Team Member and Reviewer",
                    [f"{name[0]} (Reviewer: {name[1]})" for name in grouped.groups.keys()]
                )
                selected_member, selected_reviewer = selected_group.split(" (Reviewer: ")
                selected_reviewer = selected_reviewer[:-1]

                filtered_feedback = df[(df['team_member'] == selected_member) & (df['reviewer'] == selected_reviewer)]
                st.write("### Feedback Details")
                st.dataframe(filtered_feedback)

                feedback_id = st.selectbox("Select Feedback ID to Update/Delete", filtered_feedback['id'])
                selected_feedback = filtered_feedback.loc[filtered_feedback['id'] == feedback_id]

                new_feedback = st.text_area("Update Feedback Text", selected_feedback['feedback'].iloc[0])
                new_status = st.selectbox(
                    "Update Status",
                    ["Pending", "In Progress", "Completed"],
                    index=["Pending", "In Progress", "Completed"].index(selected_feedback['status'].iloc[0])
                )

                col1, col2 = st.columns(2)
                if col1.button("Update Feedback"):
                    update_feedback(feedback_id, new_status, new_feedback)
                    st.success("Feedback updated successfully!")
                    st.rerun()

                if col2.button("Delete Feedback") and user['role'] == 'admin':
                    delete_feedback(feedback_id)
                    st.success("Feedback deleted successfully!")
                    st.rerun()
            else:
                st.warning("No feedback available to update or delete.")


        elif choice == "Manage Reviewers" and user['role'] == 'admin':
            st.subheader("Manage Reviewers")
            users_df = get_users()

            # Display Existing Users
            if not users_df.empty:
                st.write("### Existing Users")
                st.dataframe(users_df)
            else:
                st.warning("No users available.")

            # Form to Add or Update a Reviewer
            st.write("### Add or Update a Reviewer")
            reviewer_username = st.text_input("Reviewer Username")
            password = st.text_input("Password", type="password")

            # Team selection dropdown
            team = st.selectbox(
                "Assign Team",
                ["Hawk Force", "Guarding Tigers", "Speed Demons"],
                key="select_team"
            )

            # Fetch team members dynamically based on selected team
            if team:
                team_members = get_team_members(team)

                # Get default assigned members if editing an existing reviewer
                if reviewer_username in users_df['username'].values:
                    assigned_members_str = users_df.loc[users_df['username'] == reviewer_username, 'assigned_members'].values[0]
                    assigned_members_list = assigned_members_str.split(",") if assigned_members_str else []
                else:
                    assigned_members_list = []

                assigned_members = st.multiselect(
                    "Assign Team Members",
                    options=team_members,
                    default=[member.strip() for member in assigned_members_list if member.strip()],
                    key=f"assign_members_{team}"
                )
            else:
                st.warning("Please select a team to view members.")

            # Submit button to add or update reviewer
            if st.button("Save Reviewer"):
                if reviewer_username and password:
                    success = add_user(reviewer_username, password, "reviewer", team, ",".join(assigned_members))
                    if success:
                        st.success(f"Reviewer '{reviewer_username}' saved successfully!")
                        st.rerun()
                    else:
                        st.error(f"Reviewer '{reviewer_username}' already exists.")
                else:
                    st.error("Please fill in all fields.")


        elif choice == "Manage Team Mapping" and user['role'] == 'admin':
            st.subheader("Manage Team Mapping")
            users_df = get_users()
            reviewers = users_df[users_df['role'] == 'reviewer']['username'].tolist()
            if reviewers:
                selected_reviewer = st.selectbox("Select Reviewer", reviewers)
                reviewer_team = users_df.loc[users_df['username'] == selected_reviewer, 'team'].iloc[0]
                team_members = get_team_members(reviewer_team)
                current_mapping = users_df.loc[users_df['username'] == selected_reviewer, 'assigned_members'].iloc[0]
                assigned_members = st.multiselect(
                    "Assign Team Members",
                    team_members,
                    default=current_mapping.split(",") if current_mapping else []
                )

                col1, col2 = st.columns(2)
                if col1.button("Update Mapping"):
                    # Convert assigned members list to a comma-separated string
                    assigned_members_str = ",".join(assigned_members) if assigned_members else ""

                    # Update the user mapping in the database
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("""
                        UPDATE users
                        SET assigned_members = ?
                        WHERE username = ?
                    """, (assigned_members_str, selected_reviewer))
                    conn.commit()
                    conn.close()

                    st.success("Mapping updated successfully!")
                    st.rerun()
                if col2.button("Delete Mapping"):
                    delete_user_mapping(selected_reviewer)
                    st.success("Mapping deleted successfully!")
                    st.rerun()
            else:
                st.warning("No reviewers available to map.")

if __name__ == "__main__":
    main()
