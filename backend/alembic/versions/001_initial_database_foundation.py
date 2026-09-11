"""Initial database foundation for Healysis core tables

Revision ID: 001_initial_database_foundation
Revises: 
Create Date: 2026-08-26 16:47:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_database_foundation'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Facilities Table
    op.create_table(
        'facilities',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('facility_code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('facility_type', sa.Enum('PHC', 'UPHC', 'CHC', 'DISTRICT_HOSPITAL', name='facilitytype'), nullable=False),
        sa.Column('state', sa.String(length=64), nullable=False),
        sa.Column('district', sa.String(length=64), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_facilities_facility_code', 'facilities', ['facility_code'], unique=True)
    op.create_index('ix_facilities_state', 'facilities', ['state'])
    op.create_index('ix_facilities_district', 'facilities', ['district'])

    # 2. Users Table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('firebase_uid', sa.String(length=128), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('ADMIN', 'CDMO', 'FACILITY_OFFICER', name='userrole'), nullable=False),
        sa.Column('facility_id', sa.Integer(), sa.ForeignKey('facilities.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_users_firebase_uid', 'users', ['firebase_uid'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 3. Medicines Table
    op.create_table(
        'medicines',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.Enum('ESSENTIAL_MEDICINE', 'VACCINE', 'MEDICAL_SUPPLY', name='medicinecategory'), nullable=False),
        sa.Column('unit', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_medicines_code', 'medicines', ['code'], unique=True)

    # 4. Inventory Table
    op.create_table(
        'inventory',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('facility_id', sa.Integer(), sa.ForeignKey('facilities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('medicine_id', sa.Integer(), sa.ForeignKey('medicines.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('item_code', sa.String(length=64), nullable=False),
        sa.Column('item_name', sa.String(length=255), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('safety_stock', sa.Integer(), nullable=False),
        sa.Column('batch', sa.String(length=64), nullable=True),
        sa.Column('expiry', sa.Date(), nullable=True),
        sa.Column('incoming_quantity', sa.Integer(), nullable=False),
        sa.Column('unit', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('facility_id', 'medicine_id', 'batch', name='uix_facility_medicine_batch')
    )
    op.create_index('ix_inventory_facility_id', 'inventory', ['facility_id'])
    op.create_index('ix_inventory_medicine_id', 'inventory', ['medicine_id'])
    op.create_index('ix_inventory_item_code', 'inventory', ['item_code'])

    # 5. Consumption Logs Table
    op.create_table(
        'consumption_logs',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('facility_id', sa.Integer(), sa.ForeignKey('facilities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('medicine_id', sa.Integer(), sa.ForeignKey('medicines.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('item_code', sa.String(length=64), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('quantity_dispensed', sa.Integer(), nullable=False),
        sa.Column('patient_footfall', sa.Integer(), nullable=False),
        sa.Column('encounter_token', sa.String(length=64), nullable=True),
        sa.Column('action_type', sa.Enum('DISPENSE', 'RECEIVE', 'SPOILAGE', name='actiontype'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_consumption_logs_facility_id', 'consumption_logs', ['facility_id'])
    op.create_index('ix_consumption_logs_medicine_id', 'consumption_logs', ['medicine_id'])
    op.create_index('ix_consumption_logs_item_code', 'consumption_logs', ['item_code'])
    op.create_index('ix_consumption_logs_date', 'consumption_logs', ['date'])
    op.create_index('ix_consumption_logs_encounter_token', 'consumption_logs', ['encounter_token'])

    # 6. Beds Table
    op.create_table(
        'beds',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('facility_id', sa.Integer(), sa.ForeignKey('facilities.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('general_capacity', sa.Integer(), nullable=False),
        sa.Column('general_occupied', sa.Integer(), nullable=False),
        sa.Column('icu_capacity', sa.Integer(), nullable=False),
        sa.Column('icu_occupied', sa.Integer(), nullable=False),
        sa.Column('oxygen_capacity', sa.Integer(), nullable=False),
        sa.Column('oxygen_occupied', sa.Integer(), nullable=False),
        sa.Column('isolation_capacity', sa.Integer(), nullable=False),
        sa.Column('isolation_occupied', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_beds_facility_id', 'beds', ['facility_id'])

    # 7. Personnel Table
    op.create_table(
        'personnel',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('facility_id', sa.Integer(), sa.ForeignKey('facilities.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('doctors_count', sa.Integer(), nullable=False),
        sa.Column('nurses_count', sa.Integer(), nullable=False),
        sa.Column('pharmacists_count', sa.Integer(), nullable=False),
        sa.Column('asha_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_personnel_facility_id', 'personnel', ['facility_id'])

    # 8. Personnel Attendance Table
    op.create_table(
        'personnel_attendance',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('facility_id', sa.Integer(), sa.ForeignKey('facilities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('role', sa.Enum('DOCTOR', 'NURSE', 'PHARMACIST', 'ASHA', name='personnelrole'), nullable=False),
        sa.Column('scheduled', sa.Integer(), nullable=False),
        sa.Column('present', sa.Integer(), nullable=False),
        sa.Column('absent', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_personnel_attendance_facility_id', 'personnel_attendance', ['facility_id'])
    op.create_index('ix_personnel_attendance_date', 'personnel_attendance', ['date'])

    # 9. Forecasts Table
    op.create_table(
        'forecasts',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('facility_id', sa.Integer(), sa.ForeignKey('facilities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('medicine_id', sa.Integer(), sa.ForeignKey('medicines.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('item_code', sa.String(length=64), nullable=False),
        sa.Column('forecast_date', sa.Date(), nullable=False),
        sa.Column('expected_daily_demand', sa.Float(), nullable=False),
        sa.Column('days_of_cover', sa.Float(), nullable=False),
        sa.Column('projected_stockout_date', sa.Date(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('calculated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_forecasts_facility_id', 'forecasts', ['facility_id'])
    op.create_index('ix_forecasts_medicine_id', 'forecasts', ['medicine_id'])
    op.create_index('ix_forecasts_item_code', 'forecasts', ['item_code'])
    op.create_index('ix_forecasts_forecast_date', 'forecasts', ['forecast_date'])

    # 10. Alerts Table
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('alert_code', sa.String(length=64), nullable=False),
        sa.Column('facility_id', sa.Integer(), sa.ForeignKey('facilities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('resource_id', sa.String(length=64), nullable=True),
        sa.Column('severity', sa.Enum('LOW', 'WARNING', 'CRITICAL', name='alertseverity'), nullable=False),
        sa.Column('alert_type', sa.Enum('STOCKOUT_PROJECTED', 'GHOST_DRAWDOWN', 'SPOILAGE_SPIKE', 'BED_PRESSURE', 'STAFFING_DEFICIT', name='alerttype'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('evidence_json', sa.JSON(), nullable=True),
        sa.Column('projected_impact_date', sa.Date(), nullable=True),
        sa.Column('status', sa.Enum('ACTIVE', 'ACKNOWLEDGED', 'RESOLVED', name='alertstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_alerts_alert_code', 'alerts', ['alert_code'], unique=True)
    op.create_index('ix_alerts_facility_id', 'alerts', ['facility_id'])
    op.create_index('ix_alerts_resource_id', 'alerts', ['resource_id'])

    # 11. Recommendations Table
    op.create_table(
        'recommendations',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('recommendation_code', sa.String(length=64), nullable=False),
        sa.Column('donor_facility_id', sa.Integer(), sa.ForeignKey('facilities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('recipient_facility_id', sa.Integer(), sa.ForeignKey('facilities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('medicine_id', sa.Integer(), sa.ForeignKey('medicines.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('item_code', sa.String(length=64), nullable=False),
        sa.Column('recommended_quantity', sa.Integer(), nullable=False),
        sa.Column('urgency_level', sa.Enum('ROUTINE', 'URGENT', 'CRITICAL', name='urgencylevel'), nullable=False),
        sa.Column('haversine_distance_km', sa.Float(), nullable=False),
        sa.Column('expected_days_cover_gained', sa.Float(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('PENDING_HUMAN_APPROVAL', 'APPROVED', 'REJECTED', 'DISPATCHED', name='recommendationstatus'), nullable=False),
        sa.Column('reviewed_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_recommendations_recommendation_code', 'recommendations', ['recommendation_code'], unique=True)
    op.create_index('ix_recommendations_donor_facility_id', 'recommendations', ['donor_facility_id'])
    op.create_index('ix_recommendations_recipient_facility_id', 'recommendations', ['recipient_facility_id'])
    op.create_index('ix_recommendations_medicine_id', 'recommendations', ['medicine_id'])

    # 12. Requisitions Table
    op.create_table(
        'requisitions',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('req_code', sa.String(length=64), nullable=False),
        sa.Column('requester_node', sa.String(length=128), nullable=False),
        sa.Column('source_facility_id', sa.Integer(), sa.ForeignKey('facilities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_facility_id', sa.Integer(), sa.ForeignKey('facilities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('medicine_id', sa.Integer(), sa.ForeignKey('medicines.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('urgency_reason', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('PENDING_APPROVAL', 'APPROVED_AND_DISPATCHED', 'REJECTED', name='requisitionstatus'), nullable=False),
        sa.Column('reviewed_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_requisitions_req_code', 'requisitions', ['req_code'], unique=True)
    op.create_index('ix_requisitions_source_facility_id', 'requisitions', ['source_facility_id'])
    op.create_index('ix_requisitions_target_facility_id', 'requisitions', ['target_facility_id'])
    op.create_index('ix_requisitions_medicine_id', 'requisitions', ['medicine_id'])

    # 13. Audit Events Table
    op.create_table(
        'audit_events',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('event_id', sa.String(length=64), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('actor_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(length=128), nullable=False),
        sa.Column('facility_id', sa.Integer(), sa.ForeignKey('facilities.id', ondelete='SET NULL'), nullable=True),
        sa.Column('payload_json', sa.JSON(), nullable=True),
        sa.Column('previous_hash', sa.String(length=64), nullable=False),
        sa.Column('current_hash', sa.String(length=64), nullable=False),
        sa.Column('event_type', sa.Enum('TRANSACTION', 'RULE_ALERT', 'REQUISITION', 'SYSTEM', name='eventtype'), nullable=False),
        sa.Column('is_tampered', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_audit_events_event_id', 'audit_events', ['event_id'], unique=True)
    op.create_index('ix_audit_events_timestamp', 'audit_events', ['timestamp'])
    op.create_index('ix_audit_events_facility_id', 'audit_events', ['facility_id'])
    op.create_index('ix_audit_events_previous_hash', 'audit_events', ['previous_hash'])
    op.create_index('ix_audit_events_current_hash', 'audit_events', ['current_hash'])

def downgrade() -> None:
    op.drop_table('audit_events')
    op.drop_table('requisitions')
    op.drop_table('recommendations')
    op.drop_table('alerts')
    op.drop_table('forecasts')
    op.drop_table('personnel_attendance')
    op.drop_table('personnel')
    op.drop_table('beds')
    op.drop_table('consumption_logs')
    op.drop_table('inventory')
    op.drop_table('medicines')
    op.drop_table('users')
    op.drop_table('facilities')
